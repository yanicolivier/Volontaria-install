# Volontaria-install

`git clone https://github.com/Volontaria/Volontaria-install.git`

`cd Volontaria-install`

`virtualenv -p python3 env`

`source env/bin/activate`

`pip install -r requirements.txt`


The next step is to adjust the settings in the settings.py file.
Look under the localhost or dev function to adjusts the values as needed.


# Deployments
You need to have an active ssh deamon running on your local machine to make this work.

On a mac, you will need to activate this line : 

`sudo systemsetup -setremotelogin on`

There is 2 projects to install: the API and the Front-end Website.
Each of these projects need to have their project cloned and installed and also the environment (nginx and/or supervisor) if needed.

You can launch the local deployment of API and Website with this command : 

`fab localhost deploy`

You can also list the available fabric commands with : 

`fab -l`

You can decide if you want to install on a remote server by adding it name like this : 

`fab dev deploy`

There is a default dev server configuration that can be changed with the settings inside settings.py.  

If needed, you can also copy the dev function and paste it changing the name for production

In this case, you would launch the command like this : 

`fab production deploy`

