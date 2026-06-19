import os

def list_users():
    with open('/etc/passwd', 'r') as file:
        users = file.readlines()
    for user in users:
        print(user.split(':')[0])

if __name__ == "__main__":
    list_users()