import configparser
import os


class Config:
    def __init__(self):
        self.parser = configparser.RawConfigParser()
        self.parser.add_section('local')
        self.parser.add_section('auth')
        self.config_file = os.path.realpath(
            os.path.dirname(__file__) + "/../config.ini"
        )

        if os.path.exists(self.config_file):
            self.parser.read_file(open(self.config_file))

    def __del__(self):
        self.parser.write(open(self.config_file, 'w'))

    def get_dir(self):
        if self.parser:
            if self.parser.has_option('local', 'dir'):
                return self.parser.get('local', 'dir')
            else:
                value = input('Please specify where your LotI is'
                        '\nMaybe ~/.local/share/wesnoth/1.12/data/add-ons/Legend_of_the_Invincibles/ ?'
                        '\n')
                self.parser.set('local', 'dir', value)

                return value


def get_login(self):
    if self.parser:
        if self.parser.has_option('auth', 'login'):
            return self.parser.get('auth', 'login')
        else:
            value = input('Please specify your wiki login')
            self.parser.set('auth', 'login', value)

            return value


def get_pass(self):
    if self.parser:
        if self.parser.has_option('auth', 'pass'):
            return self.parser.get('auth', 'pass')
        else:
            value = input('Please specify your wiki pass')
            self.parser.set('auth', 'pass', value)

            return value
