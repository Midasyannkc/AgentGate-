# --- Networking ---

resource "aws_vpc" "agentgate" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.project_name}-vpc" }
}

resource "aws_internet_gateway" "agentgate" {
  vpc_id = aws_vpc.agentgate.id
  tags   = { Name = "${var.project_name}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.agentgate.id
  cidr_block              = var.subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"
  tags                    = { Name = "${var.project_name}-public-subnet" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.agentgate.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.agentgate.id
  }
  tags = { Name = "${var.project_name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# --- Security group ---
# SSH + k3s API (6443) restricted to admin IP. AgentGate's gateway port
# (8443, mTLS) is deliberately NOT opened to the world here — it's reached
# via kubectl port-forward or a later ingress/LB step, so this demo doesn't
# expose an agent-facing endpoint to the whole internet by default.

resource "aws_security_group" "agentgate" {
  name        = "${var.project_name}-sg"
  description = "AgentGate k3s host access"
  vpc_id      = aws_vpc.agentgate.id

  ingress {
    description = "SSH from admin IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  ingress {
    description = "k3s API from admin IP"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  ingress {
    description = "AgentGate gateway (mTLS) from admin IP, for direct testing"
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-sg" }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "k3s_host" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.agentgate.id]
  key_name               = var.key_name
  user_data              = file("${path.module}/k3s_bootstrap.sh")

  root_block_device {
    volume_size = 20
  }

  tags = {
    Name    = "${var.project_name}-k3s-host"
    Project = "AgentGate"
  }
}
