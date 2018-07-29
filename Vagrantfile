Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-16.04"
  config.vm.box_version = "201807.12.0"
  config.vm.synced_folder ".", "/epcon/project"
  config.vm.network "private_network", ip: "192.168.50.4"

  $script = <<-SCRIPT

SCRIPT
  config.vm.provision "shell", path: "vagrant/provision.sh"
  
end
