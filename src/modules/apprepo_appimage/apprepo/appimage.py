# Copyright 2020 Alex Woroschilow (alex.woroschilow@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
import configparser
import glob
import logging
import os
import pty
import shutil
import stat
import subprocess
from multiprocessing.pool import ThreadPool

from .alias import AppImageAliasFinder
from .desktop import AppImageDesktopFinder
from .icon import AppImageIconFinder
from .utils import EqualsSpaceRemover


class AppImage(object):
    pool = ThreadPool(processes=1)

    def __init__(self, locations_local=[], locations_global=[]):
        self.locations_global = locations_global
        self.locations_local = locations_local

    @property
    def locations(self):
        return self.locations_global + \
               self.locations_local

    def _permissions(self, systemwide=False):
        if systemwide is None or not systemwide:
            return stat.S_IRWXU
        return stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IRWXO | stat.S_IROTH

    def _destination(self, package, systemwide=False):
        if systemwide is None or not systemwide:
            return os.path.expanduser('~/Applications/{}'.format(package))
        return '/Applications/{}'.format(package)

    def _check(self, appimage, systemwide=False):
        logger = logging.getLogger('appimagetool')
        if not os.path.exists(appimage) or os.path.isdir(appimage):
            raise Exception('File does not exist')

        logger.debug('processing: {}'.format(appimage))
        if os.path.exists(appimage) and not os.access(appimage, os.X_OK):
            os.chmod(appimage, self._permissions(systemwide))
        out_r, out_w = pty.openpty()
        process = subprocess.Popen([appimage, '--appimage-mount'], stdout=out_w, stderr=subprocess.PIPE)
        path_mounted = str(os.read(out_r, 2048), 'utf-8', errors='ignore')
        path_mounted = path_mounted.strip("\n\r")

        path_desktop = self.get_path_desktop(systemwide)
        os.makedirs(path_desktop, exist_ok=True)

        path_icon = self.get_path_icon(systemwide)
        os.makedirs(path_icon, exist_ok=True)

        path_alias = self.get_path_alias(systemwide)
        os.makedirs(path_alias, exist_ok=True)

        desktopfinder = AppImageDesktopFinder(appimage, path_mounted)
        desktop_origin, desktop_wanted = desktopfinder.files(path_desktop)
        if not os.path.exists(desktop_origin):
            process.terminate()
            return False

        iconfinder = AppImageIconFinder(appimage, path_mounted)
        icon_origin, icon_wanted = iconfinder.files(path_icon)
        if not os.path.exists(icon_origin):
            process.terminate()
            return False

        aliasfinder = AppImageAliasFinder(appimage, path_mounted)
        alias_origin, alias_wanted = aliasfinder.files(path_alias)
        if not os.path.exists(alias_origin):
            process.terminate()
            return False

        process.terminate()

        return True

    def _integrate(self, appimage, systemwide=False):
        logger = logging.getLogger('appimagetool')
        if not os.path.exists(appimage) or os.path.isdir(appimage):
            raise Exception('File does not exist')

        logger.debug('processing: {}'.format(appimage))
        if os.path.exists(appimage) and not os.access(appimage, os.X_OK):
            os.chmod(appimage, self._permissions(systemwide))

        out_r, out_w = pty.openpty()
        process = subprocess.Popen([appimage, '--appimage-mount'], stdout=out_w, stderr=subprocess.PIPE)
        path_mounted = str(os.read(out_r, 2048), 'utf-8', errors='ignore')
        path_mounted = path_mounted.strip("\n\r")

        path_desktop = self.get_path_desktop(systemwide)
        os.makedirs(path_desktop, exist_ok=True)

        path_icon = self.get_path_icon(systemwide)
        os.makedirs(path_icon, exist_ok=True)

        path_alias = self.get_path_alias(systemwide)
        os.makedirs(path_alias, exist_ok=True)

        desktopfinder = AppImageDesktopFinder(appimage, path_mounted)
        desktop_origin, desktop_wanted = desktopfinder.files(path_desktop)
        if desktop_origin is None or desktop_wanted is None:
            logger.error('.desktop file not found for: {}'.format(appimage))
            return (None, None, None)

        iconfinder = AppImageIconFinder(appimage, path_mounted)
        icon_origin, icon_wanted = iconfinder.files(path_icon)
        if icon_origin is None or icon_wanted is None:
            logger.error('icon file not found for: {}'.format(appimage))
            return (None, None, None)

        aliasfinder = AppImageAliasFinder(appimage, path_mounted)
        alias_origin, alias_wanted = aliasfinder.files(path_alias)
        if alias_origin is None or alias_wanted is None:
            logger.error('alias file not found for: {}'.format(appimage))
            return (None, None, None)

        logger.debug('config: {}'.format(desktop_origin))
        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(desktop_origin)

        if not config.has_option('Desktop Entry', 'Version'):
            config.set('Desktop Entry', 'Version', 1.0)

        property_icon = config.get('Desktop Entry', 'Icon')
        config.set('Desktop Entry', 'Icon', iconfinder.property(property_icon))

        for section in config.sections():
            if config.has_option(section, 'Exec'):
                property_exec = config.get(section, 'Exec')
                config.set(section, 'Exec', desktopfinder.property(property_exec))

            if config.has_option(section, 'TryExec'):
                property_exec = config.get(section, 'TryExec')
                config.set(section, 'TryExec', desktopfinder.property(property_exec))

        with open(desktop_wanted, 'w') as desktop_wanted_stream:
            config.write(EqualsSpaceRemover(desktop_wanted_stream))

        with open(icon_origin, 'rb') as icon_origin_stream:
            with open(icon_wanted, 'wb') as icon_wanted_stream:
                icon_wanted_stream.write(icon_origin_stream.read())
                icon_wanted_stream.close()
            icon_origin_stream.close()

        if os.path.exists(alias_origin):
            if os.path.exists(alias_wanted):
                os.unlink(alias_wanted)
            os.symlink(alias_origin, alias_wanted)

        process.terminate()

        return (desktop_wanted, icon_wanted, alias_wanted)

    def _collection(self, location, filter=None, systemwide=False):

        patterns = ['{}/*.AppImage'.format(location)] \
            if not filter else ['{}/{}'.format(location, x) for x in filter]

        while len(patterns):
            for appimage in glob.glob(patterns.pop()):
                desktopfinder = AppImageDesktopFinder(appimage, None)
                desktop_origin, desktop_wanted = desktopfinder.files(
                    self.get_path_desktop(systemwide)
                )

                iconfinder = AppImageIconFinder(appimage, None)
                icon_origin, icon_wanted = iconfinder.files(
                    self.get_path_icon(systemwide)
                )

                aliasfinder = AppImageAliasFinder(appimage, None)
                alias_origin, alias_wanted = aliasfinder.files(
                    self.get_path_alias(systemwide)
                )

                yield (appimage, desktop_wanted, icon_wanted, alias_wanted)

    def get_path_prefix(self, systemwide=False):
        return '/usr' if systemwide else \
            os.path.expanduser('~/.local')

    def get_path_desktop(self, systemwide=False):
        return '{}/share/applications'.format(
            self.get_path_prefix(systemwide)
        )

    def get_path_icon(self, systemwide=False):
        return '{}/share/icons'.format(
            self.get_path_prefix(systemwide)
        )

    def get_path_alias(self, systemwide=False):
        return '{}/bin'.format(
            self.get_path_prefix(systemwide)
        )

    def collection(self, filter=None):

        for location in self.locations_global:
            location = os.path.expanduser(location)
            if location is None: continue

            for bunch in self._collection(location, filter, True):
                yield bunch

        for location in self.locations_local:
            location = os.path.expanduser(location)
            if location is None: continue

            for bunch in self._collection(location, filter, False):
                yield bunch

    def is_installed(self, package, systemwide=False):
        destination = self._destination(package, systemwide)
        return os.path.exists(destination)

    def install(self, tempfile, package, force=False, systemwide=False):
        destination = self._destination(package, systemwide)
        if os.path.exists(destination) and not force:
            raise Exception('{} already exists, use --force to override t'
                            'he existing package'.format(destination))

        if os.path.exists(destination):
            os.remove(destination)

        folder = os.path.dirname(destination)
        if len(folder) and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=False)

        shutil.move(tempfile, destination)
        permissions = self._permissions(systemwide)
        os.chmod(destination, permissions)

        if os.path.exists(tempfile):
            os.unlink(tempfile)

        return [destination] + self.integrate(destination, systemwide)

    def check(self, appimage, systemwide=False):
        async_result = self.pool.apply_async(self._check, (
            appimage, systemwide
        ))

        return async_result.get()

    def integrate(self, appimage, systemwide=False):
        async_result = self.pool.apply_async(self._integrate, (
            appimage, systemwide
        ))

        return list(async_result.get())
