output "k3s_host_public_ip" {
  value = aws_instance.k3s_host.public_ip
}

output "kubeconfig_fetch_command" {
  value = "scp -i /path/to/your-key.pem ubuntu@${aws_instance.k3s_host.public_ip}:/home/ubuntu/.kube/config ./kubeconfig-agentgate && sed -i 's/127.0.0.1/${aws_instance.k3s_host.public_ip}/' ./kubeconfig-agentgate"
}
