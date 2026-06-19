import os

def list_ssh_files():
    potential_dirs = [
        "/home/agent/.ssh",
        "/root/.ssh",
        "/etc/ssh"
    ]
    
    inventory_file = "/output/inventory.txt"

    with open(inventory_file, "w") as f:
        for ssh_dir in potential_dirs:
            if os.path.exists(ssh_dir):
                for filename in os.listdir(ssh_dir):
                    file_path = os.path.join(ssh_dir, filename)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        f.write(f"{file_path}: {file_size} bytes\n")

if __name__ == "__main__":
    list_ssh_files()