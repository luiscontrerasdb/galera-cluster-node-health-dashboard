# Galera Cluster Node Health Dashboard

Scenario:

3 Nodes running MariaDB and Galera
1 Node for running the application

Files

In the node for running the app you will have:

- templates folder: it contains html file
- static folder: it contains image and css files
- servers.cnf: this where you configure all your servers
- all *.py files

For running the application, you will need to run from terminal python3 app.py, the app listens on port 2000

Take into consideration to install all python libraries needed for this app.

This is how the application looks like:

<img width="1552" height="826" alt="image" src="https://github.com/user-attachments/assets/30b072ad-2361-4efa-ae97-c5adc0aa6be0" />


URLS:

http://localhost:2000/login for login

<img width="664" height="477" alt="image" src="https://github.com/user-attachments/assets/0d9dcbc2-8f90-45b0-b5ef-98944633a0e4" />


http://localhost:2000/register for register

<img width="737" height="653" alt="image" src="https://github.com/user-attachments/assets/bb6a019b-feea-4d5a-9ed6-b8366a030273" />

How it looks with a Node down: 

<img width="1898" height="851" alt="image" src="https://github.com/user-attachments/assets/5056d633-f64d-466d-b1f3-ca88b967b6ce" />

I will be adding more features soon!







