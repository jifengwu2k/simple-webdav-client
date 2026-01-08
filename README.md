# `simple-dav-client`

A minimal, robust command-line client for interacting with a WebDAV server over plain HTTP with no authentication.

## Features

- **List** (`ls`): List remote files or directories.
- **Upload** (`put`): Upload local files or directories (recursively) to a remote directory.
- **Download** (`get`): Download remote files or directories (recursively) to a local directory.
- **Create** (`mkdir`): Create directories on the remote server (optionally recursively).
- **Remove** (`rm`): Delete remote files or directories (recursively).

## Design

This tool is designed for **maximum clarity and correctness**:

- ✅ **No Authentication / No HTTPS**: This client uses only HTTP (not HTTPS), and does not support authentication,
  cookies, or custom headers. Simplicity was prioritized for trusted, local/test servers.
- ✅ **Fail Fast & Loudly**: If any network, connection, or server error occurs, the tool will abort and display an error
  message. **No retry, fallback, or silent handling** is implemented by design.
- ✅ **Path Tokenization**: All local and remote paths are tokenized using the [
  `fspathverbs`](https://github.com/jifengwu2k/fspathverbs) library, and all internal APIs use tokenized paths. This
  ensures reliable, traversal-safe handling and robust operation across platforms and server configurations.
- ✅ **Recursive Operations**: Both uploads and downloads automatically **recurse** into directories, preserving
  directory hierarchies for both local-to-remote and remote-to-local transmissions.
    - This client uses the classic **Command Pattern**.
        - All uploads (`put`) and downloads (`get`) are performed by first **compiling** a list of `PutAction` and
          `GetAction` operation objects that **describe exactly what needs to be done**, then **executing** in strict
          order.
        - This allows for clean error reporting, separation of planning and execution, and makes future extensions (
          logging, dry runs, previews, etc.) straightforward.
- ✅ **Strong Code Separation**: Command-line parsing/dispatch is cleanly separated from the core logic for clarity and
  maintainability.

## Installation

```commandline
pip install simple-dav-client
```

## Usage

List a remote file or directory:

```commandline
python -m simple_dav_client --host localhost --port 8080 ls /remote/file-or-directory
```

Download a remote file or directory to `./local`:

```commandline
python -m simple_dav_client --host localhost --port 8080 get -O ./local /remote/file-or-directory
```

Upload a local file or directory to `/remote`:

```commandline
python -m simple_dav_client --host localhost --port 8080 put -O /remote ./local/file-or-directory
```

Create a remote directory (including parent directories):

```commandline
python -m simple_dav_client --host localhost --port 8080 mkdir -p /remote/child-directory
```

Remove a remote file or directory:

```commandline
python -m simple_dav_client --host localhost --port 8080 rm /remote/file-or-directory
```

## Contributing

Contributions are welcome! Please submit pull requests or open issues on the GitHub repository.

## License

This project is licensed under the [MIT License](LICENSE).