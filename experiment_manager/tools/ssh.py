# based on https://gist.githubusercontent.com/johnfink8/2190472/raw/e4f3df6dde23309d3228986d0a1cc39c0a6ed9ac/ssh.py

import paramiko
import errno
import socket
import os
from stat import S_ISDIR
import getpass
from Crypto.PublicKey import RSA
import socket
import time
#from scp import SCPClient

class SSHSession(object):
    def __init__(self, hostname, username=None, port = 22, password=None, key_file=None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        home = os.environ['HOME']
        if key_file is None:
            self.key_file = '{}/.ssh/id_rsa'.format(home)
        elif key_file[0] == '/':
            self.key_file = key_file
        elif os.path.isfile('{}/.ssh/{}/id_rsa'.format(home,key_file)):
            self.key_file = '{}/.ssh/{}/id_rsa'.format(home,key_file)
        elif os.path.isfile(key_file):
            self.key_file = key_file
        else:
            self.key_file = '{}/.ssh/id_rsa'.format(home)

        self.client = paramiko.SSHClient()
        self.connect()

    def connect(self):
        home = os.environ['HOME']
        self.client.load_system_host_keys()
        try:
            self.client.connect(hostname=self.hostname, username=self.username, port=self.port, password=self.password, key_filename=self.key_file)
        except:
            time.sleep(1)
            retry = True
            while retry:
                try:
                    self.client.connect(hostname=self.hostname, username=self.username, port=self.port, password=self.password, key_filename=self.key_file)
                except:
                    a = raw_input('Connection failed. Retry? Y/N/catch')
                    if a == 'catch':
                        raise
                    elif a not in ['y','Y']:
                        retry = False
            if not retry:
                temp_password = getpass.getpass('SSH Password:')
                self.client.connect(hostname=self.hostname, username=self.username, port=self.port, password=temp_password, key_filename=None)
                question = raw_input('Install SSH key? Y/N')
                if question == 'Y' or question == 'y':
                    where = raw_input('Where? default (~/.ssh/id_rsa) / key_file (<key_file>) / key_file_name (~/.ssh/<key_file>/id_rsa) / <path>')
                    if where == 'default':
                        where = '{}/.ssh/id_rsa'.format(home)
                    elif where == 'key_file_name':
                        where = '{}/.ssh/{}/id_rsa'.format(home,self.key_file)
                    elif where == 'key_file':
                        where = self.key_file
                    self.key_file = where
                    self.install_ssh_key()
                    self.close()
                    self.client.connect(hostname=self.hostname, username=self.username, port=self.port, password=self.password, key_filename=self.key_file)
        self.transport = self.client._transport
        self.transport.window_size = 2147483647
        self.transport.packetizer.REKEY_BYTES = pow(2, 40)
        self.transport.packetizer.REKEY_PACKETS = pow(2, 40)
        #self.scp = SCPClient(self.transport)
        self.sftp = self.client.open_sftp()

    def reconnect(self):
        self.close()
        self.connect()

    def path_exists(self, path):
        try:
            self.sftp.stat(path)
        except IOError, e:
            if e.errno == errno.ENOENT:
                return False
            raise e
        else:
            return True

    def mkdir_p(self, path):
        if path in ['/','','.','~']:
            return None
        else:
            try:
                self.sftp.stat(path)
            except IOError:
                dirname, basename = os.path.split(path.rstrip('/'))
                self.mkdir_p(dirname)
                self.sftp.mkdir(path)

    def create_path(self, path):
        self.mkdir_p(path)
        #self.command_output("mkdir -p {}".format(path))

    def command(self,cmd):
        return self.client.exec_command(cmd)

    def command_output(self,cmd):
        std_in, std_out, std_err = self.client.exec_command(cmd)
        return std_out.read()

    def put(self,localfile,remotefile):
        #if not self.path_exists(os.path.dirname(remotefile)):
        #    self.create_path(os.path.dirname(remotefile))
        try:
            self.sftp.put(localfile,remotefile)
        except IOError:
            self.create_path(os.path.dirname(remotefile))
            self.sftp.put(localfile,remotefile)

    def put_dir(self,localdir,remotedir, max_depth=10):
        if max_depth<0:
            raise Exception('Directory too deep!')
        files = os.listdir(localdir)
        for f in files:
            if os.path.isfile(os.path.join(localdir,f)):
                #if not self.path_exists(remotedir):
                #    self.create_path(remotedir)
                self.put(os.path.join(localdir,f),os.path.join(remotedir,f))
            else:
                self.put_dir(os.path.join(localdir,f),os.path.join(remotedir,f),max_depth=max_depth-1)

    def get(self,remotefile,localfile):
        self.sftp.get(remotefile,localfile)

    def get_dir(self,remotedir,localdir,max_depth=10):
        if max_depth<0:
            raise Exception('Directory too deep!')
        files = self.sftp.listdir(remotedir)
        for f in files:
            f = str(f)
            if not self.isdir(os.path.join(remotedir,f)):
                self.get(os.path.join(remotedir,f),os.path.join(localdir,f))
            else:
                if not os.path.exists(os.path.join(localdir,f)):
                    os.makedirs(os.path.join(localdir,f))
                self.get_dir(os.path.join(remotedir,f),os.path.join(localdir,f),max_depth=max_depth-1)

    def rm(self, path):
        self.command('rm -R '+path)

    def isdir(self, path):
      try:
        return S_ISDIR(self.sftp.stat(path).st_mode)
      except IOError:
        #Path does not exist, so by definition not a directory
        return False

    def close(self):
        self.client.close()

    def install_ssh_key(self):
        path = os.path.dirname(self.key_file)
        if not os.path.exists(path):
            os.makedirs(path)
        if os.path.isfile(self.key_file) or os.path.isfile(self.key_file+'.pub'):
            raise Exception('Keys already exist!')
        key = RSA.generate(2048)
        with open(self.key_file, 'w') as content_file:
            os.chmod(self.key_file, 0600)
            content_file.write(key.exportKey('PEM'))
        pubkey = key.publickey()
        pubkey_string = pubkey.exportKey('OpenSSH') + ' {}@{}'.format(os.environ['USER'], socket.gethostname())
        with open(self.key_file+'.pub', 'w') as content_file:
            content_file.write(pubkey_string)
        self.command('echo -e "{}" >> /home/{}/.ssh/authorized_keys'.format(pubkey_string, self.username))


