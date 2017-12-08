import os
import time

from fabric.api import *
from fabric.contrib.files import exists
from contextlib import contextmanager as _contextmanager

from jinja2 import Environment, FileSystemLoader

from tempfile import mkstemp
from shutil import move
from os import fdopen, remove

from settings import *

LOCAL_OUTPUT_PATH = 'output'
LOCAL_TEMPLATE_PATH = './templates'

BASE_GIT_PATH = 'https://github.com/Volontaria'

env.use_ssh_config = True

"""
Function Helper
"""


def run_custom(*args, **kwargs):
    func = local if env.host == "localhost" else run
    return func(*args, **kwargs)


def cd_custom(*args, **kwargs):
    func = lcd if env.host == "localhost" else cd
    return func(*args, **kwargs)


def base_create_file(j2_env=None, config={}):
    if not j2_env:
        j2_env = Environment(loader=FileSystemLoader(LOCAL_TEMPLATE_PATH), trim_blocks=True)

    render = j2_env.get_template(config['template_path']).render(
        port=config['port'],
        path=config['path'],
        base_path=config['base_path'],
        domain=config['domain'],
        name=config['name'],
        user=config['user'],
        ssl=config['ssl'],
        ssl_cert_path=config['ssl_cert_path'],
        ssl_key_path=config['ssl_key_path']
    )

    if not os.path.exists('./%s/%s/%s' % (LOCAL_OUTPUT_PATH, env.name, config['template_path'])):
        os.makedirs('./%s/%s/%s' % (LOCAL_OUTPUT_PATH, env.name, config['template_path']))

    with open("./%s/%s/%s/%s" % (LOCAL_OUTPUT_PATH, env.name, config['template_path'], config['output_name']), "w") as f:
        f.write(render)


def replace_in_file(file_path, pattern, subst):
    # Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line.replace(pattern, subst))
    # Remove original file
    remove(file_path)
    # Move new file
    move(abs_path, file_path)


def get_api_base_path(real_path=False):
    if real_path:
        return env.api_base_path
    else:
        return "%s/%s_NEW" % (env.api_install_path, API_GIT_PROJECT_NAME)


def get_api_project_path(real_path=False):
    if real_path:
        return env.api_project_path
    else:
        return '%s/source' % get_api_base_path(real_path)


def get_web_base_path(real_path=False):
    if real_path:
        return env.web_base_path
    else:
        return "%s/%s_NEW" % (env.web_install_path, WEB_GIT_PROJECT_NAME)


"""
General functions
"""


@task
def deploy():
    api_deploy()
    web_deploy()


"""
API functions
"""


@task
def api_deploy():
    rep = api_project_install()

    if rep:
        api_update(must_ask_req=False, real_path=False)

        with settings(warn_only=True):
            real_base_path = get_api_base_path(True)
            run_custom('sudo mv %s %s_OLD' % (real_base_path, real_base_path))
            run_custom('sudo mv %s_NEW %s' % (real_base_path, real_base_path))

        if env.api_use_nginx or env.api_use_supervisor:
            msg = prompt("Need to create/update nginx and supervisor ?: "
                         "(y)es, (n)o", default="y/n").lower()

            if msg == 'y':
                api_setup_env()

        # Restart supervisor
        if env.api_use_supervisor:
            run_custom('sudo supervisorctl restart %s' % API_NAME)


@_contextmanager
def api_virtualenv():
    with cd_custom(env.api_install_path):
        with prefix('source %s/API-env/bin/activate' % env.api_install_path):
            yield


def api_delete_create_db():
    if env.api_use_db:
        if env.api_db_engine == 'django.db.backends.mysql':
            with hide('output', 'running', 'warnings'), settings(warn_only=True):
                output = run_custom("""mysql -u%s -p%s -e 'USE %s'""" % (env.api_db_user, env.api_db_password, env.api_db_name))

            if 'Unknown database' in output:
                print('DB not existing...')
            else:
                msg = prompt("Database %s already exist, what do you want to do: "
                             "(o)verwrite, (l)eave" % env.api_db_name, default="o/l").lower()
                if msg == 'o':
                    print('Deleting and recreating database %s' % env.api_db_name)

                    with hide('output', 'running', 'warnings'), settings(warn_only=True):
                        run_custom('mysql -u%s -p%s -e "DROP DATABASE IF EXISTS %s"' % (
                        env.api_db_user, env.api_db_password, env.api_db_name))
                        result = run_custom(
                            'mysqladmin -u %s -p%s create %s' % (env.api_db_user, env.api_db_password, env.api_db_name))

                    if result.succeeded:
                        print('Success')
                    else:
                        print('Failed')

                else:
                    print('Leaving Database alone...')
                    return

        else:
            print("Unsupported DB type... Aborting...")


@task
def api_project_install():
    with settings(warn_only=True):
        run_custom('mkdir %s' % env.api_install_path)

    if exists(get_api_base_path(True)):
        msg = prompt("There is already an installation of %s, do you want to: "
                     "(a)bort, (r)eplace and continue" % API_NAME, default="a/r").lower()
        if msg == 'a':
            print('Aborting')
            return False

        with settings(warn_only=True):
            #removing NEW
            run_custom('sudo rm -r %s' % get_api_base_path(False))

    # Clone project
    with cd_custom(env.api_install_path):
        run_custom('git clone %s/%s.git %s_NEW' % (BASE_GIT_PATH, API_GIT_PROJECT_NAME, API_GIT_PROJECT_NAME))

    with cd_custom(get_api_project_path(False)):
        # Create virtualenv
        if not exists('%s/API-env/' % env.api_install_path):
            run_custom('virtualenv -p python3 %s/API-env/' % env.api_install_path)

        run_custom('git checkout %s' % env.api_git_branch)

        if env.api_use_nginx or env.api_use_supervisor:
            run_custom('mkdir %s/source/log' % get_api_base_path(False))

        local_settings_path = '%s/apiVolontaria/apiVolontaria/local_settings.py' % get_api_project_path(False)

        # Add lines into local_settings.py file
        run_custom("""echo "\n# APPENDED FROM VOLONTARIA-INSTALL\n" >> %s""" % local_settings_path)

        run_custom("""echo "ALLOWED_HOSTS = ['%s', ]" >> %s""" % (env.api_domain, local_settings_path))

        run_custom("""echo "DEBUG = %s" >> %s""" % (env.api_debug, local_settings_path))

        if env.api_use_db:
            run_custom("""echo "\n\nDATABASES = {" >> %s""" % local_settings_path)
            run_custom("""echo "\t'default': {" >> %s""" % local_settings_path)
            run_custom("""echo "\t\t'ENGINE': '%s'," >> %s""" % (env.api_db_engine, local_settings_path))
            run_custom("""echo "\t\t'NAME': '%s'," >> %s""" % (env.api_db_name, local_settings_path))
            run_custom("""echo "\t\t'USER': '%s'," >> %s""" % (env.api_db_user, local_settings_path))
            with hide('output', 'running', 'warnings'), settings(warn_only=True):
                run_custom("""echo "\t\t'PASSWORD': '%s'," >> %s""" % (env.api_db_password, local_settings_path))
            run_custom("""echo "\t\t'HOST': '%s'," >> %s""" % (env.api_db_host, local_settings_path))
            run_custom("""echo "\t}\n}\n" >> %s""" % local_settings_path)

        run_custom("""echo "TIME_ZONE = 'Canada/Eastern'" >> %s""" % local_settings_path)

        """
        CONSTANT = {
            "EMAIL_SERVICE": False,
            "AUTO_ACTIVATE_USER": False,
            "FRONTEND_INTEGRATION": {
                "ACTIVATION_URL": "example.com/activate?activation_token={{token}}",
            },
        }
        """

        run_custom("""echo "\n\nCONSTANT = {" >> %s""" % local_settings_path)
        run_custom("""echo "\t'EMAIL_SERVICE': True," >> %s""" % local_settings_path)
        run_custom("""echo "\t'AUTO_ACTIVATE_USER': False," >> %s""" % local_settings_path)
        run_custom("""echo "\t'FRONTEND_INTEGRATION': {" >> %s""" % local_settings_path)
        run_custom("""echo "\t\t'ACTIVATION_URL': '%s/register/activation/{{token}}'," >> %s""" % (env.web_domain, local_settings_path))
        run_custom("""echo "\t}\n}\n" >> %s""" % local_settings_path)

        """
        # Email service configuration.
        # Supported services: SendinBlue.
        SETTINGS_IMAILING = {
            "SERVICE": "SendinBlue",
            "API_KEY": "example_api_key",
            "EMAIL_FROM": "admin@example.com",
            "TEMPLATES": {
                "CONFIRM_SIGN_UP": "example_template_id"
            }
        }
        """

        run_custom("""echo "\n\nSETTINGS_IMAILING = {" >> %s""" % local_settings_path)
        run_custom("""echo "\t'SERVICE': '%s'," >> %s""" % (env.api_email_service, local_settings_path))
        run_custom("""echo "\t'API_KEY': '%s'," >> %s""" % (env.api_email_api_key, local_settings_path))
        run_custom("""echo "\t'EMAIL_FROM': '%s'," >> %s""" % (env.api_email_from, local_settings_path))
        run_custom("""echo "\t'TEMPLATES': {" >> %s""" % local_settings_path)
        run_custom("""echo "\t\t'CONFIRM_SIGN_UP': '%s'," >> %s""" % (env.api_email_template_confirm_id, local_settings_path))
        run_custom("""echo "\t}\n}\n" >> %s""" % local_settings_path)

        run_custom("""echo "\n" >> %s""" % local_settings_path)

        return True


@task
def api_update(must_ask_req=True, real_path=False):
    with cd_custom(get_api_project_path(real_path)):
        run_custom('git pull origin %s' % env.api_git_branch)

    with api_virtualenv():
        if must_ask_req:
            msg = prompt("Would you like to install the requirements ?: "
                         "(y)es, (n)o", default="y/n").lower()
        else:
            msg = 'y'

        if msg == 'y':
            # Install Requirements
            run_custom('pip install -r %s/requirements.txt' % get_api_base_path(real_path))
            run_custom('pip install gunicorn')

        if env.api_use_db:
            if msg == 'y':
                run_custom('pip install mysqlclient')
            api_delete_create_db()

        with cd_custom("%s/apiVolontaria" % get_api_project_path(real_path)):
            # Django Commands to initialize the project
            run_custom('python manage.py migrate')

            if env.api_use_nginx:
                run_custom('python manage.py collectstatic')

            msg = prompt("Would you like to create a superuser ?: "
                         "(y)es, (n)o", default="y/n").lower()
            if msg == 'y':
                run_custom('python manage.py createsuperuser')

    # Restart supervisor
    if env.api_use_supervisor and real_path:
        run_custom('sudo supervisorctl restart %s' % API_NAME)


@task
def api_setup_env():
    j2_env = Environment(loader=FileSystemLoader('./templates'), trim_blocks=True)

    if env.api_use_nginx:
        config = {
            'template_path': 'api/nginx',
            'output_name': env.api_nginx_file_output_name,
            'port': env.api_port,
            'path': get_api_base_path(True),
            'base_path': env.api_install_path,
            'domain': env.api_domain,
            'name': API_NAME,
            'user': env.user,
            'ssl': env.api_use_ssl,
            'ssl_cert_path': '%s/%s' % (env.api_ssl_remote_path, env.api_ssl_cert),
            'ssl_key_path': '%s/%s' % (env.api_ssl_remote_path, env.api_ssl_key),
        }

        base_create_file(j2_env, config)

    if env.api_use_supervisor:
        config = {
            'template_path': 'api/supervisor',
            'output_name': env.api_supervisor_file_output_name,
            'port': env.api_port,
            'path': get_api_base_path(True),
            'base_path': env.api_install_path,
            'domain': env.api_domain,
            'name': API_NAME,
            'user': env.user,
            'ssl': env.api_use_ssl,
            'ssl_cert_path': '%s/%s' % (env.api_ssl_remote_path, env.api_ssl_cert),
            'ssl_key_path': '%s/%s' % (env.api_ssl_remote_path, env.api_ssl_key),
        }

        base_create_file(j2_env, config)

    # Send create files to remote server
    local("scp -r ./%s/%s %s@%s:%s" % (LOCAL_OUTPUT_PATH, env.name, env.user, env.hosts[0], env.installer_path))

    if env.api_use_ssl:
        with settings(warn_only=True):
            run_custom('mkdir %s' % env.api_ssl_remote_path)

        local('scp -r ./%s/%s %s@%s:%s/%s' % (
        env.api_ssl_local_path, env.api_ssl_cert, env.user, env.hosts[0], env.api_ssl_remote_path, env.api_ssl_cert))
        local('scp -r ./%s/%s %s@%s:%s/%s' % (
        env.api_ssl_local_path, env.api_ssl_key, env.user, env.hosts[0], env.api_ssl_remote_path, env.api_ssl_key))

    with settings(warn_only=True):
        run_custom('sudo rm %s' % env.installer_path)

    if env.api_use_nginx:
        run_custom('sudo cp %s/api/nginx/%s /etc/nginx/sites-available/%s' % (
            env.installer_path, env.api_domain, env.api_domain))
    
        # Create symbolic link in site enabled
        with cd_custom('/etc/nginx/sites-available/'):
            with settings(warn_only=True):
                run_custom('sudo ln -s /etc/nginx/sites-available/%s /etc/nginx/sites-enabled/%s' % (
                    env.api_domain, env.api_domain
                ))
    
        output = run_custom('sudo nginx -t')
    
        if 'syntax is ok' in output:
            run_custom('sudo service nginx reload')
        else:
            print('--- Error restarting nginx ! ---')

    if env.api_use_supervisor:
        run_custom('sudo cp %s/api/supervisor/%s /etc/supervisor/conf.d/%s' % (
            env.installer_path, env.api_supervisor_file_output_name, env.api_supervisor_file_output_name))
    
        with settings(warn_only=True):
            run_custom('sudo supervisorctl stop %s' % API_NAME)
            run_custom('sudo supervisorctl remove %s' % API_NAME)
    
        run_custom('sudo supervisorctl reread')
        run_custom('sudo supervisorctl add %s' % API_NAME)
        run_custom('sudo supervisorctl status')

    with settings(warn_only=True):
        run_custom('sudo rm -r %s' % env.installer_path)


"""
Website-Volontaria
"""


@task
def web_deploy():
    web_project_install()
    web_update(False)

    with settings(warn_only=True):
        real_base_path = get_web_base_path(True)
        run_custom('sudo mv %s %s_OLD' % (real_base_path, real_base_path))
        run_custom('sudo mv %s_NEW %s' % (real_base_path, real_base_path))

    msg = prompt("Need to create/update nginx ?: "
                 "(y)es, (n)o", default="y/n").lower()

    if msg == 'y':
        web_setup_env()




@task
def web_setup_env():
    if env.web_use_nginx:
        j2_env = Environment(loader=FileSystemLoader('./templates'), trim_blocks=True)

        config = {
            'template_path': 'web/nginx',
            'output_name': env.web_nginx_file_output_name,
            'port': env.web_port,
            'path': get_web_base_path(True),
            'base_path': env.web_install_path,
            'domain': env.web_domain,
            'name': WEB_NAME,
            'user': env.user,
            'ssl': env.api_use_ssl,
            'ssl_cert_path': '%s/%s' % (env.web_ssl_remote_path, env.web_ssl_cert),
            'ssl_key_path': '%s/%s' % (env.web_ssl_remote_path, env.web_ssl_key),
        }

        base_create_file(j2_env, config)

        # Send create files to remote server
        local('scp -r ./%s/%s %s@%s:%s' % (LOCAL_OUTPUT_PATH, env.name, env.user, env.hosts[0], env.installer_path))

        if env.web_use_ssl:
            with settings(warn_only=True):
                run_custom('mkdir %s' % env.api_ssl_remote_path)

            local('scp -r ./%s/%s %s@%s:%s/%s' % (env.web_ssl_local_path, env.web_ssl_cert, env.user, env.hosts[0], env.web_ssl_remote_path, env.web_ssl_cert))
            local('scp -r ./%s/%s %s@%s:%s/%s' % (env.web_ssl_local_path, env.web_ssl_key, env.user, env.hosts[0], env.web_ssl_remote_path, env.web_ssl_key))

        run_custom('sudo cp %s/web/nginx/%s /etc/nginx/sites-available/%s' % (env.installer_path, env.web_domain, env.web_domain))

        # Create symbolic link in site enabled
        with cd_custom('/etc/nginx/sites-available/'):
            with settings(warn_only=True):
                run_custom('sudo ln -s /etc/nginx/sites-available/%s /etc/nginx/sites-enabled/%s' % (
                    env.web_domain, env.web_domain
                ))

        output = run_custom('sudo nginx -t')

        if 'syntax is ok' in output:
            run_custom('sudo service nginx reload')
        else:
            print('--- Error restarting nginx ! ---')
    else:
        print('Nothing to do...')

    with settings(warn_only=True):
        run_custom('sudo rm -r %s' % env.installer_path)


@task
def web_project_install():
    with settings(warn_only=True):
        run_custom('mkdir %s' % env.web_install_path)

    if exists(get_web_base_path(True)):
        msg = prompt("There is already an installation of %s, do you want to: "
                     "(a)bort, (c)ontinue" % WEB_NAME, default="a/c").lower()
        if msg == 'a':
            print('Aborting')
            return

    with settings(warn_only=True):
        # removing NEW
        run_custom('sudo rm -r %s' % get_web_base_path(False))

    # Clone project
    with cd_custom(env.web_install_path):
        run_custom('git clone %s/%s.git %s_NEW' % (BASE_GIT_PATH, WEB_GIT_PROJECT_NAME, WEB_GIT_PROJECT_NAME))

    with cd_custom(get_web_base_path(False)):
        run_custom('git checkout %s' % env.web_git_branch)
        run_custom('mkdir %s/log' % get_web_base_path(False))


@task
def web_update(real_path=True):
    with cd_custom(get_web_base_path(real_path)):
        run_custom('git checkout %s' % env.web_git_branch)
        run_custom('git pull origin %s' % env.web_git_branch)

        if env.api_use_ssl:
            api_domain = 'https:\/\/%s' % env.api_domain
        else:
            api_domain = 'http:\/\/%s' % env.api_domain

        path = '%s/src/environments/environment.prod.ts' % (get_web_base_path(False),)
        print(path)

        run_custom('sed "s/http:\/\/localhost:8000/%s/g" %s > %s.GOOD' % (api_domain, path, path))
        run_custom('rm %s' % path)
        run_custom('mv %s.GOOD %s' % (path, path))

        run_custom('npm install')
        run_custom('ng build -prod -locale fr')
