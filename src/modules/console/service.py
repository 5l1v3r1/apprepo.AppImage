# -*- coding: utf-8 -*-
# Copyright 2015 Alex Woroschilow (alex.woroschilow@gmail.com)
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


class Console(object):

    def status(self, options=None, args=None):
        from .task import status
        for entity in status.main(options, args):
            yield entity

    def synchronize(self, options=None, args=None):
        from .task import synchronize
        for entity in synchronize.main(options, args):
            yield entity

    def cleanup(self, options=None, args=None):
        from .task import cleanup
        for entity in cleanup.main(options, args):
            yield entity

    def search(self, options=None, args=None):
        from .task import search
        for entity in search.main(options, args):
            yield entity

    def install(self, options=None, args=None):
        from .task import install
        for entity in install.main(options, args):
            yield entity

    def uninstall(self, options=None, args=None):
        from .task import uninstall
        for entity in uninstall.main(options, args):
            yield entity

    def update(self, options=None, args=None):
        from .task import update
        for entity in update.main(options, args):
            yield entity

    def upload(self, options=None, args=None):
        from .task import upload
        for entity in upload.main(options, args):
            yield entity

    #     if path is None or not len(path):
    #         raise Exception('File path can not be empty')
    #
    #     if not os.path.exists(path) or os.path.isdir(path):
    #         raise Exception('File does not exist: {}'.format(path))
    #
    #     if options is None or not options:
    #         raise Exception('Please setup version options')
    #
    #     if options.version_token is None or not len(options.version_token):
    #         raise Exception('token not found')
    #
    #     if options.version_description is None or not len(options.version_description):
    #         raise Exception('description not found')
    #
    #     if options.version_name is None or not len(options.version_name):
    #         raise Exception('name not found')
    #
    #     url_initialize = "{}/package/upload/initialize/".format(self.api)
    #     url_finalize = '{}/package/upload/complete/finalize/'.format(self.api)
    #     task = VersionUploadTask(url_initialize, url_finalize)
    #
    #     result = task.upload(path, {
    #         'token': options.version_token,
    #         'description': options.version_description,
    #         'name': options.version_name,
    #     })
    #
    #     if result is None or not result:
    #         raise Exception('Result can not be empty')
    #
    #     yield 'Uploaded: {} {} - {}, {}'.format(
    #         result['package'] or 'Unknown',
    #         result['version'] or 'Unknown',
    #         result['description'] or 'Unknown',
    #         path or 'Unknown'
    #     )
