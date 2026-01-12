# Copyright (c) 2026 Jifeng Wu
# Licensed under the MIT License. See LICENSE file in the project root for full license information.
from __future__ import print_function

import argparse
import os
import posixpath
import sys

import xml.etree.ElementTree as ElementTree
from typing import BinaryIO, Sequence, Iterator, Tuple

if sys.version_info < (3,):
    from urllib import quote, unquote
else:
    from urllib.parse import quote, unquote

import requests
from cowlist import COWList
from fspathverbs import Root, Parent, Current, Child, compile_to_fspathverbs


class ListResult(object):
    """Base class for results of listing a remote path."""
    pass


class IsDirectory(ListResult):
    """
    Represents a remote directory listing result.

    Args:
        containing_file_path_components (Sequence[Sequence[str]]): Path components of files in directory.
        containing_directory_path_components (Sequence[Sequence[str]]): Path components of subdirectories.
    """

    def __init__(
            self,
            containing_file_path_components,  # type: Sequence[Sequence[str]]
            containing_directory_path_components,  # type: Sequence[Sequence[str]]
    ):
        self.containing_file_path_components = containing_file_path_components  # type: Sequence[Sequence[str]]
        self.containing_directory_path_components = containing_directory_path_components  # type: Sequence[Sequence[str]]

    def __repr__(self):
        return '%s(containing_file_path_components=%r, containing_directory_path_components=%r)' % (
            self.__class__.__name__,
            self.containing_file_path_components,
            self.containing_directory_path_components
        )

    def __reduce__(self):
        return self.__class__, (self.containing_file_path_components, self.containing_directory_path_components)

    def __hash__(self):
        return hash(self.__reduce__())

    def __eq__(self, other):
        return self.__reduce__() == other.__reduce__()


class IsFile(ListResult):
    """
    Represents a remote file listing result.

    Args:
        file_path_components (Sequence[str]): Path components of the file.
    """

    def __init__(
            self,
            file_path_components,  # type: Sequence[str]
    ):
        self.file_path_components = file_path_components  # Sequence[str]

    def __repr__(self):
        return '%s(file_path_components=%r)' % (self.__class__.__name__, self.file_path_components)

    def __reduce__(self):
        return self.__class__, (self.file_path_components,)

    def __hash__(self):
        return hash(self.__reduce__())

    def __eq__(self, other):
        return self.__reduce__() == other.__reduce__()


class NotFound(ListResult):
    """Indicates the remote path was not found."""

    def __repr__(self):
        return '%s()' % (self.__class__.__name__,)

    def __reduce__(self):
        return self.__class__, ()

    def __hash__(self):
        return hash(self.__reduce__())

    def __eq__(self, other):
        return self.__reduce__() == other.__reduce__()


class GetAction(object):
    """Base class for actions required in get (download) operations."""
    pass


class DownloadRemoteFile(GetAction):
    """
    Describes an action to download a remote file.

    Args:
        remote_file_path_components (Sequence[str]): Remote file path components.
        relative_local_file_path_components (Sequence[str]): Relative local file path components to save file as.
    """

    def __init__(
            self,
            remote_file_path_components,  # type: Sequence[str]
            relative_local_file_path_components,  # type: Sequence[str]
    ):
        self.remote_file_path_components = remote_file_path_components  # type: Sequence[str]
        self.relative_local_file_path_components = relative_local_file_path_components  # type: Sequence[str]

    def __repr__(self):
        return '%s(remote_file_path_components=%r, relative_local_file_path_components=%r)' % (
            self.__class__.__name__,
            self.remote_file_path_components,
            self.relative_local_file_path_components,
        )

    def __reduce__(self):
        return self.__class__, (self.remote_file_path_components, self.relative_local_file_path_components)

    def __hash__(self):
        return hash(self.__reduce__())

    def __eq__(self, other):
        return self.__reduce__() == other.__reduce__()


class CreateLocalDirectory(GetAction):
    """
    Describes an action to create a local directory.

    Args:
        relative_local_directory_path_components (Sequence[str]): Relative local directory path components to make.
    """

    def __init__(
            self,
            relative_local_directory_path_components,  # type: Sequence[str]
    ):
        self.relative_local_directory_path_components = relative_local_directory_path_components  # type: Sequence[str]

    def __repr__(self):
        return '%s(relative_local_directory_path_components=%r)' % (
            self.__class__.__name__,
            self.relative_local_directory_path_components
        )

    def __reduce__(self):
        return self.__class__, (self.relative_local_directory_path_components,)

    def __hash__(self):
        return hash(self.__reduce__())

    def __eq__(self, other):
        return self.__reduce__() == other.__reduce__()


class PutAction(object):
    """Base class for actions required in put (upload) operations."""
    pass


class UploadLocalFile(PutAction):
    """
    Describes an action to upload a local file.

    Args:
        local_file_path (str): Local file path.
        relative_remote_file_path_components (Sequence[str]): Relative remote file path components to save file as.
    """

    def __init__(
            self,
            local_file_path,  # type: str
            relative_remote_file_path_components,  # type: Sequence[str]
    ):
        self.local_file_path = local_file_path  # type: str
        self.relative_remote_file_path_components = relative_remote_file_path_components  # type: Sequence[str]

    def __repr__(self):
        return '%s(local_file_path=%r, relative_remote_file_path_components=%r)' % (
            self.__class__.__name__,
            self.local_file_path,
            self.relative_remote_file_path_components,
        )

    def __reduce__(self):
        return self.__class__, (self.local_file_path, self.relative_remote_file_path_components)

    def __hash__(self):
        return hash(self.__reduce__())

    def __eq__(self, other):
        return self.__reduce__() == other.__reduce__()


class CreateRemoteDirectory(PutAction):
    """
    Describes an action to create a remote directory.

    Args:
        relative_remote_directory_path_components (Sequence[str]): Relative remote directory path components to make.
    """

    def __init__(
            self,
            relative_remote_directory_path_components,  # type: Sequence[str]
    ):
        self.relative_remote_directory_path_components = relative_remote_directory_path_components  # type: Sequence[str]

    def __repr__(self):
        return '%s(relative_remote_directory_path_components=%r)' % (
            self.__class__.__name__,
            self.relative_remote_directory_path_components
        )

    def __reduce__(self):
        return self.__class__, (self.relative_remote_directory_path_components,)

    def __hash__(self):
        return hash(self.__reduce__())

    def __eq__(self, other):
        return self.__reduce__() == other.__reduce__()


def relative_local_path_to_relative_local_path_components(
        relative_local_path,  # type: str
):
    # type: (...) -> Sequence[str]
    """
    Split and normalize a relative local path string into a list of path components.

    Args:
        relative_local_path (str): The relative local path string.

    Returns:
        Sequence[str]: List of normalized path components.
    """
    components = COWList()
    verbs = compile_to_fspathverbs(path=relative_local_path, split=os.path.split)
    for verb in verbs:
        if isinstance(verb, Parent):
            if components:
                components, _ = components.pop()
            else:
                raise ValueError('Invalid relative local path: %s' % relative_local_path)
        elif isinstance(verb, Current):
            pass
        elif isinstance(verb, Child):
            components = components.append(verb.child)
        else:
            raise ValueError('Invalid relative local path: %s' % relative_local_path)

    return components


def remote_path_to_remote_path_components(
        remote_path,  # type: str
):
    # type: (...) -> COWList[str]
    """
    Split and normalize a remote (posix style) path string into a list of path components.

    Args:
        remote_path (str): The remote file/directory path string.

    Returns:
        COWList[str]: List of normalized path components.
    """
    components = COWList()
    verbs = compile_to_fspathverbs(path=remote_path, split=posixpath.split)
    for verb in verbs:
        if isinstance(verb, Root):
            components = components.clear()
        elif isinstance(verb, Parent):
            if components:
                components, _ = components.pop()
            else:
                raise ValueError('Invalid remote path: %s' % remote_path)
        elif isinstance(verb, Current):
            pass
        elif isinstance(verb, Child):
            components = components.append(verb.child)

    return components


def remote_path_components_to_href(
        host,  # type: str
        port,  # type: int
        remote_path_components,  # type: Sequence[str]
):
    # type: (...) -> str
    """
    Convert remote path components to a full HTTP WebDAV HREF.

    Args:
        host (str): Hostname.
        port (int): Port.
        remote_path_components (Sequence[str]): List of path segments.

    Returns:
        str: HTTP HREF string.
    """
    return 'http://%s:%d/%s' % (host, port, '/'.join(map(quote, remote_path_components)))


def href_to_remote_path_components(
        host,  # type: str
        port,  # type: int
        href,  # type: str
):
    # type: (...) -> COWList[str]
    """
    Convert a HREF to remote path components.

    Args:
        host (str): Hostname.
        port (int): Port.
        href (str): WebDAV resource HREF.

    Returns:
        COWList[str]: List of decoded path segments.
    """
    base = 'http://%s:%d' % (host, port)
    if href.startswith(base):
        # base_href resembles http://localhost:8080/foo/bar
        relative_path = posixpath.relpath(href, base)
    elif href.startswith('/'):
        # base_href resembles /foo/bar
        relative_path = href[1:]
    else:
        raise ValueError('Invalid href: %s' % href)

    components = COWList()
    verbs = compile_to_fspathverbs(path=relative_path, split=posixpath.split)
    for verb in verbs:
        if isinstance(verb, Root):
            raise ValueError('Invalid href: %s' % href)
        elif isinstance(verb, Parent):
            if components:
                components, _ = components.pop()
            else:
                raise ValueError('Invalid href: %s' % href)
        elif isinstance(verb, Current):
            pass
        elif isinstance(verb, Child):
            components = components.append(unquote(verb.child))

    return components


def iterate_put_actions(
        local_path,  # type: str,
        relative_remote_path_prefix=COWList(),  # type: COWList[str]
):
    # type: (...) -> Iterator[PutAction]
    """
    Recursively generate 'put' (upload) actions required to upload
    a local file or directory to a remote location.

    Args:
        local_path (str): Local file or directory to upload.
        relative_remote_path_prefix (COWList[str], optional): Path prefix on the remote side.

    Yields:
        PutAction: UploadLocalFile or CreateRemoteDirectory actions.
    """
    absolute_local_path = os.path.abspath(local_path)
    basename = os.path.basename(absolute_local_path)

    if basename and os.path.isfile(absolute_local_path):
        yield UploadLocalFile(
            local_file_path=absolute_local_path,
            relative_remote_file_path_components=relative_remote_path_prefix.append(basename),
        )
    elif basename and os.path.isdir(absolute_local_path):
        relative_remote_path_prefix_with_basename = relative_remote_path_prefix.append(basename)
        yield CreateRemoteDirectory(
            relative_remote_directory_path_components=relative_remote_path_prefix_with_basename,
        )
        for dirpath, dirnames, filenames in os.walk(absolute_local_path):
            relative_local_path_components = relative_local_path_to_relative_local_path_components(
                relative_local_path=os.path.relpath(dirpath, absolute_local_path),
            )

            new_relative_remote_path_prefix = relative_remote_path_prefix_with_basename.extend(
                relative_local_path_components
            )

            for dirname in dirnames:
                yield CreateRemoteDirectory(
                    relative_remote_directory_path_components=new_relative_remote_path_prefix.append(dirname),
                )

            for filename in filenames:
                yield UploadLocalFile(
                    local_file_path=os.path.join(dirpath, filename),
                    relative_remote_file_path_components=new_relative_remote_path_prefix.append(filename),
                )
    else:
        raise ValueError('Invalid local path: %s' % local_path)


class SimpleDAVClient(object):
    def __init__(
            self,
            host='localhost',  # type: str
            port=8080,  # type: int
    ):
        """
        Initialize the client with host and port.

        Args:
            host (str): WebDAV server hostname.
            port (int): WebDAV server port.
        """
        self.host = host  # type: str
        self.port = port  # type: int
        self.session = requests.session()

    # These methods directly make requests
    # These methods operate on sanitized path components
    def iterate_listings_and_is_directories(
            self,
            remote_path_components,  # type: Sequence[str]
    ):
        # type: (...) -> Iterator[Tuple[Sequence[str], bool]]
        """
        Iterate over items in the directory at the given path,
        yielding (path_components, is_directory) for each.

        Args:
            remote_path_components (Sequence[str]): Normalized path components of the target.

        Yields:
            Tuple[Sequence[str], bool]: (path_components, is_directory) for each child resource.
        """
        remote_path_href = remote_path_components_to_href(
            host=self.host,
            port=self.port,
            remote_path_components=remote_path_components
        )

        response = self.session.request(
            method='PROPFIND',
            url=remote_path_href,
            headers={'Depth': '1'},
        )

        if response.status_code == 207:
            tree = ElementTree.fromstring(response.content)
            for dav_response_node in tree.findall('{DAV:}response'):
                dav_response_dav_href_node = dav_response_node.find('.//{DAV:}href')
                if dav_response_dav_href_node is not None:
                    dav_response_dav_href = dav_response_dav_href_node.text
                    if dav_response_dav_href is not None:
                        dav_response_dav_collection_node = dav_response_node.find('.//{DAV:}collection')
                        dav_response_dav_resourcetype_node = dav_response_node.find('.//{DAV:}resourcetype')
                        if dav_response_dav_resourcetype_node is not None:
                            dav_response_dav_resourcetype_dav_collection_node = dav_response_dav_resourcetype_node.find(
                                '{DAV:}collection'
                            )
                        else:
                            dav_response_dav_resourcetype_dav_collection_node = None

                        is_collection = (
                                dav_response_dav_collection_node is not None
                                or dav_response_dav_resourcetype_dav_collection_node is not None
                        )

                        yield href_to_remote_path_components(
                            host=self.host,
                            port=self.port,
                            href=dav_response_dav_href
                        ), is_collection

    def create_directory_from_remote_path_components(
            self,
            remote_path_components,  # type: Sequence[str]
    ):
        # type: (...) -> bool
        """
        Create a directory at the given remote path (single level).

        Args:
            remote_path_components (Sequence[str]): Path components for the new directory.

        Returns:
            bool: True on success, False otherwise.
        """
        remote_path_href = remote_path_components_to_href(
            host=self.host,
            port=self.port,
            remote_path_components=remote_path_components
        )

        response = self.session.request(
            method='MKCOL',
            url=remote_path_href,
        )

        if response.status_code == 201:
            return True
        else:
            return False

    def put_file_to_remote_path_components(
            self,
            binary_file,  # type: BinaryIO
            remote_path_components,  # type: Sequence[str]
    ):
        # type: (...) -> bool
        """
        Upload a binary file object to the specified remote path.

        Args:
            binary_file (BinaryIO): Open file object to upload.
            remote_path_components (Sequence[str]): Path components for the new file.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        remote_path_href = remote_path_components_to_href(
            host=self.host,
            port=self.port,
            remote_path_components=remote_path_components
        )

        response = self.session.request(
            method='PUT',
            url=remote_path_href,
            data=binary_file,
        )

        if response.status_code in (200, 201, 204):
            return True
        else:
            return False

    def get_file_from_remote_path_components(
            self,
            remote_path_components,  # type: Sequence[str]
    ):
        # type: (...) -> Iterator[bytes]
        """
        Stream and yield the contents of a file from the given remote path.

        Args:
            remote_path_components (Sequence[str]): Path components of the file.

        Yields:
            bytes: Chunks of file data.
        """
        remote_path_href = remote_path_components_to_href(
            host=self.host,
            port=self.port,
            remote_path_components=remote_path_components
        )

        response = self.session.request(
            method='GET',
            url=remote_path_href,
            stream=True,
        )

        if response.status_code == 200:
            for chunk in response.iter_content(chunk_size=None):
                yield chunk

    def delete_file_or_directory_from_remote_path_components(
            self,
            remote_path_components,  # type: Sequence[str]
    ):
        """
        Delete a remote file or directory at the specified path.

        Args:
            remote_path_components (Sequence[str]): Path components of the remote file or directory.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
        remote_path_href = remote_path_components_to_href(
            host=self.host,
            port=self.port,
            remote_path_components=remote_path_components
        )

        response = self.session.request(
            method='DELETE',
            url=remote_path_href,
        )

        if response.status_code == 204:
            return True
        else:
            return False

    # These methods wrap methods that directly make requests
    # These methods operate on sanitized path components
    def list_remote_file_or_directory(
            self,
            remote_path_components,  # type: Sequence[str]
    ):
        # type: (...) -> ListResult
        """
        List the remote file or directory at the given path.

        Args:
            remote_path_components (Sequence[str]): Path components of the file or directory.

        Returns:
            ListResult: IsFile, IsDirectory, or NotFound.
        """
        listings_to_is_directories = dict(
            self.iterate_listings_and_is_directories(remote_path_components=remote_path_components)
        )
        if remote_path_components not in listings_to_is_directories:
            return NotFound()
        elif not listings_to_is_directories[remote_path_components]:
            return IsFile(file_path_components=remote_path_components)
        else:
            file_path_components = COWList()
            directory_path_components = COWList()
            del listings_to_is_directories[remote_path_components]
            for listing, is_directory in listings_to_is_directories.items():
                if is_directory:
                    directory_path_components = directory_path_components.append(listing)
                else:
                    file_path_components = file_path_components.append(listing)
            return IsDirectory(
                containing_file_path_components=file_path_components,
                containing_directory_path_components=directory_path_components,
            )

    def create_directories_from_remote_path_components(
            self,
            remote_path_components,  # type: Sequence[str]
    ):
        # type: (...) -> bool
        """
        Recursively create parent directories for the specified path.

        Args:
            remote_path_components (Sequence[str]): Path components for directory hierarchy.

        Returns:
            bool: True on total success, False otherwise.
        """
        # The root directory always exists
        if not remote_path_components:
            return True
        # Try directly making the final directory
        elif self.create_directory_from_remote_path_components(remote_path_components=remote_path_components):
            return True
        # If that doesn't work, try making n-1 levels of directories
        elif self.create_directories_from_remote_path_components(remote_path_components=remote_path_components[:-1]):
            # Then try directly making the final directory again
            return self.create_directory_from_remote_path_components(remote_path_components=remote_path_components)
        else:
            return False

    def iterate_get_actions(
            self,
            remote_path_components,  # type: Sequence[str],
            relative_local_path_prefix=COWList(),  # type: COWList[str]
    ):
        # type: (...) -> Iterator[GetAction]
        """
        Generate a sequence of actions required to get a remote file or directory.

        Args:
            remote_path_components (Sequence[str]): Path to remote file or directory.
            relative_local_path_prefix (COWList[str], optional): Relative local path prefix for the current level.

        Yields:
            GetAction: Either DownloadRemoteFile or MakeLocalDirectories.
        """
        list_result = self.list_remote_file_or_directory(remote_path_components=remote_path_components)
        if isinstance(list_result, IsFile):
            remote_file_path_components = list_result.file_path_components
            yield DownloadRemoteFile(
                remote_file_path_components=remote_file_path_components,
                relative_local_file_path_components=relative_local_path_prefix.append(remote_file_path_components[-1])
            )
        elif isinstance(list_result, IsDirectory):
            if not remote_path_components:
                # This remote directory is root
                # Do not change local path prefix
                new_relative_local_path_prefix = relative_local_path_prefix
            else:
                # This remote directory is not root
                # Update the local path prefix with the remote directory name
                # Make a corresponding local directory
                new_relative_local_path_prefix = relative_local_path_prefix.append(remote_path_components[-1])
                yield CreateLocalDirectory(relative_local_directory_path_components=new_relative_local_path_prefix)

            # Download containing files to new local path prefix
            for file_path_components in list_result.containing_file_path_components:
                yield DownloadRemoteFile(
                    remote_file_path_components=file_path_components,
                    relative_local_file_path_components=new_relative_local_path_prefix.append(file_path_components[-1])
                )

            # Recurse on containing directories
            for directory_path_components in list_result.containing_directory_path_components:
                for get_action in self.iterate_get_actions(
                        remote_path_components=directory_path_components,
                        relative_local_path_prefix=new_relative_local_path_prefix,
                ):
                    yield get_action

    # These methods operate on paths instead of sanitized path components
    def ls(
            self,
            remote_path,  # type: str
    ):
        """
        List the remote file or directory. Used for the 'ls' command.

        Args:
            remote_path (str): The path to list.
        """
        remote_path_components = remote_path_to_remote_path_components(remote_path=remote_path)
        list_result = self.list_remote_file_or_directory(remote_path_components=remote_path_components)
        if isinstance(list_result, IsFile):
            print(list_result.file_path_components[-1])
        elif isinstance(list_result, IsDirectory):
            for file_path_components in list_result.containing_file_path_components:
                print(file_path_components[-1])
            for directory_path_components in list_result.containing_directory_path_components:
                print(directory_path_components[-1] + '/')
        else:
            print('cannot list %s' % (remote_path,), file=sys.stderr)

    def mkdir(
            self,
            remote_directory_path,  # type: str
            p,  # type: bool
    ):
        """
        Create remote directory at given path, optionally recursively. Used for the 'mkdir' command.

        Args:
            remote_directory_path (str): The directory path to create.
            p (bool): If True, create all parent directories as needed.
        """
        remote_path_components = remote_path_to_remote_path_components(remote_path=remote_directory_path)
        if p:
            if not self.create_directories_from_remote_path_components(remote_path_components=remote_path_components):
                print('cannot create remote directory %s' % (remote_directory_path,), file=sys.stderr)
        else:
            if not self.create_directory_from_remote_path_components(remote_path_components=remote_path_components):
                print('cannot create remote directory %s' % (remote_directory_path,), file=sys.stderr)

    def put(
            self,
            remote_directory_path,  # type: str
            local_path,  # type: str
    ):
        """
        Upload a file or directory (recursively) to the specified remote directory.

        Args:
            remote_directory_path (str): Remote directory path to upload into.
            local_path (str): Local file or directory to upload.
        """
        remote_path_components = remote_path_to_remote_path_components(remote_path=remote_directory_path)
        for put_action in iterate_put_actions(local_path=local_path):
            if isinstance(put_action, CreateRemoteDirectory):
                self.create_directory_from_remote_path_components(
                    remote_path_components=remote_path_components.extend(
                        put_action.relative_remote_directory_path_components,
                    )
                )
            elif isinstance(put_action, UploadLocalFile):
                local_file_path = put_action.local_file_path
                remote_file_path_components = remote_path_components.extend(
                    put_action.relative_remote_file_path_components,
                )
                with open(local_file_path, 'rb') as f:
                    self.put_file_to_remote_path_components(
                        binary_file=f,
                        remote_path_components=remote_file_path_components,
                    )
                    print('%s -> %s' % (local_file_path, '/'.join(remote_file_path_components)))

    def get(
            self,
            local_directory_path,  # type: str
            remote_path,  # type: str
    ):
        """
        Download remote file or directory to target local directory. Used for the 'get' command.

        Args:
            local_directory_path (str): Where to create downloaded files/directories.
            remote_path (str): File or directory to download from the server.
        """
        remote_path_components = remote_path_to_remote_path_components(remote_path=remote_path)
        for get_action in self.iterate_get_actions(remote_path_components=remote_path_components):
            if isinstance(get_action, CreateLocalDirectory):
                local_directory_to_create_path = os.path.join(
                    local_directory_path,
                    *get_action.relative_local_directory_path_components
                )
                if not os.path.isdir(local_directory_to_create_path):
                    os.mkdir(local_directory_to_create_path)
            elif isinstance(get_action, DownloadRemoteFile):
                remote_file_path_components = get_action.remote_file_path_components
                local_file_path = os.path.join(local_directory_path, *get_action.relative_local_file_path_components)
                with open(local_file_path, 'wb') as f:
                    for chunk in self.get_file_from_remote_path_components(
                            remote_path_components=remote_file_path_components
                    ):
                        f.write(chunk)
                    print('%s -> %s' % ('/'.join(remote_file_path_components), local_file_path))

    def rm(
            self,
            remote_path,  # type: str
    ):
        """
        Remove a remote file or directory.

        Args:
            remote_path (str): Path of the remote file or directory to remove.
        """
        remote_path_components = remote_path_to_remote_path_components(remote_path=remote_path)
        if self.delete_file_or_directory_from_remote_path_components(remote_path_components=remote_path_components):
            print('removed %s' % (remote_path,))
        else:
            print('cannot remove %s' % (remote_path,), file=sys.stderr)


def main():
    # Top-level parser
    parser = argparse.ArgumentParser(description='Simple DAV Client')
    parser.add_argument('--host', type=str, default='localhost', help='WebDAV server hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=8080, help='WebDAV server port (default: 8080)')
    subparsers = parser.add_subparsers(dest='command')

    # ls command
    ls_parser = subparsers.add_parser('ls', help='List remote file or directory')
    ls_parser.add_argument('remote_path', type=str, nargs='?', help='Remote file or directory')

    # mkdir command
    mkdir_parser = subparsers.add_parser('mkdir', help='Create remote directory')
    mkdir_parser.add_argument('remote_directory_path', type=str, help='Remote directory')
    mkdir_parser.add_argument('-p', action='store_true', help='Make parent directories as needed')

    # put command
    put_parser = subparsers.add_parser('put', help='Upload remote file or directory to remote directory')
    put_parser.add_argument(
        '-O',
        '--remote-directory-path',
        type=str,
        default='/',
        help='Remote directory where to save'
    )
    put_parser.add_argument(
        'local_paths',
        metavar='local_path',
        type=str,
        nargs='+',
        help='Local file or directory (one or more) to upload'
    )

    # get command
    get_parser = subparsers.add_parser('get', help='Download remote file or directory to local directory')
    get_parser.add_argument(
        '-O',
        '--local-directory-path',
        type=str,
        default='.',
        help='Local directory where to save'
    )
    get_parser.add_argument(
        'remote_paths',
        metavar='remote_path',
        type=str,
        nargs='+',
        help='Remote file or directory (one or more) to download'
    )

    # rm command
    rm_parser = subparsers.add_parser('rm', help='Remove remote file or directory')
    rm_parser.add_argument(
        'remote_paths',
        metavar='remote_path',
        type=str,
        nargs='+',
        help='Remote file or directory (one or more) to remove'
    )

    args = parser.parse_args()

    # Create client
    client = SimpleDAVClient(host=args.host, port=args.port)

    # Dispatch commands
    if args.command == 'ls':
        client.ls(remote_path=args.remote_path or '/')
    elif args.command == 'mkdir':
        client.mkdir(remote_directory_path=args.remote_directory_path, p=args.p)
    elif args.command == 'put':
        for local_path in args.local_paths:
            client.put(remote_directory_path=args.remote_directory_path, local_path=local_path)
    elif args.command == 'get':
        for remote_path in args.remote_paths:
            client.get(local_directory_path=args.local_directory_path, remote_path=remote_path)
    elif args.command == 'rm':
        for remote_path in args.remote_paths:
            client.rm(remote_path=remote_path)
    else:
        parser.error('argument subcommand: not provided (choose from %s)' % (', '.join(subparsers.choices.keys()),))


if __name__ == '__main__':
    main()
