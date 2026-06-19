import os

def list_files(directory):
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            try:
                size = os.path.getsize(file_path)
                files.append((file_path, size))
            except PermissionError:
                continue
    return files

def main():
    directories = ['/home/agent/.ssh', '/root/.ssh', '/etc/ssh', '~/.aws']
    inventory = []
    
    for directory in directories:
        if os.path.exists(directory):
            inventory.extend(list_files(directory))
    
    with open('/output/inventory.txt', 'w') as output_file:
        for file_path, size in inventory:
            output_file.write(f"{file_path} {size}\n")

if __name__ == "__main__":
    main()