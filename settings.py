# -*- coding: utf-8 -*-

from fabric.api import *

"""
Local configurations
"""
LOCAL_LINUX_USER = 'john'

LOCAL_BASE_PATH = '/Users/john/workspace'

"""
API-Volontaria configurations
"""

API_GIT_PROJECT_NAME = 'API-Volontaria'

# The name of the module
API_NAME = "api"

"""
Website-Volontaria configurations
"""

# The name of the module
WEB_NAME = "web"

WEB_GIT_PROJECT_NAME = 'Website-Volontaria'

"""
The configuation to install the projects locally
"""
@task
def localhost():
    """
    GLOBALS
    """
    env.name = 'local'

    # The name of the ssh config name and also the /etc/hosts name (must be the same)
    env.hosts = ['localhost']

    # The name of the remote Linux user that will have right over the project
    env.user = 'john'

    # The path of the ssh key in local computer to be able to connect to remote server
    env.key_filename = '~/.ssh/id_rsa'

    env.installer_path = '/home/%s/Volontaria-install-helper' % env.user

    """
    API
    """

    env.api_git_branch = 'develop'

    env.api_install_path = '/home/john'
    env.api_base_path = "%s/%s" % (env.api_install_path, API_GIT_PROJECT_NAME)
    env.api_project_path = '%s/source' % env.api_base_path

    env.api_domain = '127.0.0.1'
    #env.api_port = 100

    env.api_debug = True

    # NGINX
    env.api_use_nginx = False
    # The name of the nginx file
    #env.api_nginx_file_output_name = env.api_domain

    # SUPERVISOR
    env.api_use_supervisor = False
    # The name of the supervisor config file
    #env.api_supervisor_file_output_name = 'supervisor_api_volontaria.conf'

    """
    API-Email
    """
    env.api_email_service = "SendinBlue"
    env.api_email_api_key = "XXX"
    env.api_email_from = "john@domain.com"
    env.api_email_template_confirm_id = 1

    """
    Database configurations (used if env.api_use_db is True)
    """

    env.api_use_db = False

    # env.api_db_engine = 'django.db.backends.mysql'
    #
    # # DB Name
    # env.api_db_name = ''
    #
    # # DB User
    # env.api_db_user = ''
    #
    # # DB Password
    # env.api_db_password = ''
    #
    # # DB Host
    # env.api_db_host = 'localhost'

    """
    WEB
    """

    env.web_git_branch = 'develop'

    #env.web_domain = 'web.domain.com'
    #env.web_port = 101

    # The path where the project will be cloned on the remote server
    env.web_install_path = '/home/john'
    env.web_base_path = "%s/%s" % (env.web_install_path, WEB_GIT_PROJECT_NAME)

    # NGINX
    env.web_use_nginx = False
    #env.web_nginx_file_output_name = env.web_domain

    """
    SSL
    """

    env.api_use_ssl = False
    env.api_ssl_local_path = ''
    env.api_ssl_remote_path = ''
    env.api_ssl_cert = ''
    env.api_ssl_key = ''

    env.web_use_ssl = env.api_use_ssl
    env.web_ssl_local_path = env.api_ssl_local_path
    env.web_ssl_remote_path = env.api_ssl_remote_path
    env.web_ssl_cert = env.api_ssl_cert
    env.web_ssl_key = env.api_ssl_key


"""
The configuation to install the projects on a remote server
"""
@task
def dev():
    """
    GLOBALS
    """
    env.name = 'dev'

    # The name of the ssh config name and also the /etc/hosts name (must be the same)
    env.hosts = ['remote_server']

    # The name of the remote Linux user that will have right over the project
    env.user = 'john'

    # The path of the ssh key in local computer to be able to connect to remote server
    env.key_filename = '~/.ssh/id_rsa'

    env.installer_path = '/home/%s/Volontaria-install-helper' % env.user


    """
    API
    """

    env.api_git_branch = 'develop'

    env.api_install_path = '/home/john'
    env.api_base_path = "%s/%s" % (env.api_install_path, API_GIT_PROJECT_NAME)
    env.api_project_path = '%s/source' % env.api_base_path

    env.api_domain = 'api.domain.com'
    env.api_port = 100

    env.api_debug = False

    # NGINX
    env.api_use_nginx = True
    # The name of the nginx file
    env.api_nginx_file_output_name = env.api_domain

    # SUPERVISOR
    env.api_use_supervisor = True
    # The name of the supervisor config file
    env.api_supervisor_file_output_name = 'api_volontaria.conf'

    """
    API-Email
    """
    env.api_email_service = "SendinBlue"
    env.api_email_api_key = "XXX"
    env.api_email_from = "john@domain.com"
    env.api_email_template_confirm_id = 1


    """
    Database configurations (used if env.api_use_db is True)
    """

    env.api_use_db = True

    env.api_db_engine = 'django.db.backends.mysql'

    # DB Name
    env.api_db_name = 'db_api'

    # DB User
    env.api_db_user = ''

    # DB Password
    env.api_db_password = ''

    # DB Host
    env.api_db_host = 'localhost'


    """
    WEB
    """

    env.web_git_branch = 'develop'

    env.web_domain = 'web.domain.com'
    env.web_port = 101

    # The path where the project will be cloned on the remote server
    env.web_install_path = '/home/john'
    env.web_base_path = "%s/%s" % (env.web_install_path, WEB_GIT_PROJECT_NAME)

    # NGINX
    env.web_use_nginx = True
    env.web_nginx_file_output_name = env.web_domain

    """
    SSL
    """

    env.api_use_ssl = False
    env.api_ssl_local_path = './ssl_files'
    env.api_ssl_remote_path = '%s/ssl_files' % env.api_install_path
    env.ssl_cert = '%s/1234.crt'
    env.ssl_key = '%s/1234.key'

    env.web_use_ssl = env.api_use_ssl
    env.web_ssl_local_path = env.api_ssl_local_path
    env.web_ssl_remote_path = env.api_ssl_remote_path
    env.web_ssl_cert = env.api_ssl_cert
    env.web_ssl_key = env.api_ssl_key


try:
    from local_settings import *
except Exception as e:
    pass
