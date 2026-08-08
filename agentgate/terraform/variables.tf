variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "agentgate"
}

variable "instance_type" {
  description = "Sized for a lightweight single-node k3s cluster"
  type        = string
  default     = "t3.medium"
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH access"
  type        = string
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR form, e.g. 1.2.3.4/32"
  type        = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "subnet_cidr" {
  type    = string
  default = "10.40.1.0/24"
}
