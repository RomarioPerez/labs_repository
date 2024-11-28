value=$(less /boot/grub/grub.cfg | grep Windows | awk -F "'" '{print $2}')
if [ -n "$value" ]; then
  sudo sed -i "s/^GRUB_DEFAULT=.*/GRUB_DEFAULT='$value'/" /etc/default/grub
fi

