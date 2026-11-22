xapblr
======

Locally index Tumblr blogs in a xapian database for advanced searching.
Think `notmuch`, but for Tumblr.

## Setup

### Installation

#### If you run Arch:
`xapblr` uses @nostalgebraist's [fork of `pytumblr`](https://github.com/nostalgebraist/pytumblr2).
It's not on the AUR, but you can [build it as an Arch package](https://github.com/skircheis/python-pytumblr2-PKGBUILD/tree/master).
```sh
git clone https://github.com/skircheis/python-pytumblr2-PKGBUILD python-pytumblr2-git
cd python-pytumblr2-git
makepkg -is
```
Then repeat the procedure for `xapblr`:
```
git clone https://github.com/skircheis/xapblr-PKGBUILD xapblr
cd xapblr
makepkg -is
```

#### Otherwise, with `uv`
The Xapian Python bindings are not available from PyPI, so install them from your distribution first
(`python-xapian` on Arch, `python3-xapian` on Debian/Ubuntu, `python3-xapian` on Fedora).
Then create a virtual environment that can see them and install `xapblr` into it:
```sh
uv venv --system-site-packages --python /usr/bin/python3 ~/.local/share/xapblr/venv
uv pip install --python ~/.local/share/xapblr/venv \
    git+https://github.com/transhumanist-atom-understander/xapblr
ln -s ~/.local/share/xapblr/venv/bin/xapblr ~/.local/bin/xapblr
```
`--python /usr/bin/python3` must be the interpreter your distribution's Xapian bindings were built for.
(`uv tool install` is not suitable because it cannot give the environment access to system packages.)

The base install covers indexing, searching, listing and rebuilding.
Optional features are available as extras:

| Extra           | Enables                                        |
|-----------------|------------------------------------------------|
| `web`           | the web interface (`flask`, `flask-assets`)    |
| `clip`          | the CLIP captioning agent (`pillow`, `open-clip-torch`) |
| `humanfriendly` | nicer relative timestamps in messages          |
| `all`           | all of the above                               |

E.g. `uv pip install --python ~/.local/share/xapblr/venv "xapblr[web] @ git+https://github.com/transhumanist-atom-understander/xapblr"`.

To work on `xapblr` from a checkout, `uv venv --system-site-packages --python /usr/bin/python3`, then `uv sync --all-extras`.

If you use the web interface under `uwsgi`, also install `uwsgi` and its Python plugin from your distribution and run
```sh
sudo cp -t /etc/uwsgi config/uwsgi/xapblr.ini
```
so `uwsgi` can find `xapblr`'s web interface.

## Configuration and initialisation

`xapblr` requires a a Tumblr API key, which you can obtain [by registering the app with Tumblr](https://www.tumblr.com/oauth/apps) and then [obtaining authentication data](https://api.tumblr.com/console/calls/user/info).
`xapblr` expects to find this authentication data in `$XDG_CONFIG_HOME/xapblr/APIKEY`, in JSON format like so:
```json
{
    "consumer_key": <consumer_key>,
    "consumer_secret": <consumer_secret>,
    "oauth_token": <oauth_token>,
    "oauth_secret": <oauth_secret>
}
```
Although this is not enforced, for security the `APIKEY` file should be readable only by its
owner.

`xapblr` stores its data in `$XDG_DATA_HOME/share/xapblr/`; by default this
should be `~/.local/share/xapblr`.

You can now initialise the index of your blog thus:
```sh
xapblr index --full <your-blog-url>
```
This may take some time due to rate limits, see [below](#initialisation-and-rate-limiting).
The index is regularly committed to disk, so you can put this process in the background and start looking around;
try `xapblr search --help` and see `[SEARCH.md](SEARCH.MD)`.

`systemd` units are provided for regular re-indexing.
Viz.,
```sh
systemctl --user enable --now xapblr-hourly@<your-blog-url>
systemctl --user enable --now xapbl-daily@<your-blog-url>
```
for hourly and daily re-indexing, respectively.

## Web interface

This requires the `web` extra, and the `sass` and `pandoc` executables.
More convenient than the command line is the web interface.
Launch it with
```sh
uwsgi --ini /etc/uwsgi/xapblr.ini
```
or as a `systemd` service
```sh
systemd --user enable --now xapblr-web
```
Then open http://localhost:5000/.

### Configuring the web interface

The web interface listens on port `5000` by default.
If you need to change this or any other `uwsgi` configuration copy the INI file (`/etc/uwsgi/xapblr.ini`), edit it as appropriate, and run from there, instead.
E.g.,
```sh
uwsgi --ini ~/.config/xapblr/uwsgi.ini
```
If running as a `systemd` service, repoint it through `systemctl --user edit xapblr-web`.

## CLIP generation of captions

`xapblr` can caption images in posts using [Open CLIP](https://github.com/mlfoundations/open_clip).
Because this is costly, it is optional and runs asynchronously on a client-server model.
To enable captioning, first configure an authentication token and a server profile in `$XDG_CONFIG_HOME/xapblr/config.json`:
```json
{
    ...
    "clip": {"auth_token": <secret> },
    "clip_agent": {
        "servers": {
            "localhost": {
                "endpoint": "http://localhost:5000/clip",
                "auth_token": <secret>
            }
        }
    }
    ...
}
```
Then install the `clip` extra (which pulls in Open CLIP) and launch a captioning agent
```sh
uv pip install --python ~/.local/share/xapblr/venv "xapblr[clip] @ git+https://github.com/transhumanist-atom-understander/xapblr"
xapblr clip localhost
```
The agent will loop fetching a batch of tasks from `http://localhost:5000/clip`, trying to caption them with Open CLIP, and submitting the results back to the server.
If there are no tasks available the agent sleeps before checking again;
the time slept can be set with the `--sleep` argument or as `clip_agent.sleep = N` in the configuration file.
As you may have guessed a captioning agent does not need to run on the same machine as the server.
Simply configure the endpoint and authentication token as appropriate.
Likewise, any number of captioning agents can run against the same server.
An optional `clip_agent.agent_id` can be provided for the server to know which agent captioned an image;
it can be set with `--agent-id` on the command line.
The default is to use the hostname of the machine running the agent.

Clip agents can be run as systemd units.
Viz. in the above case we would run
```sh
systemctl --user enable --now xapblr-clip-agent@localhost
```

## Rebuilding

As `xapblr` is developed the indexing of posts may change to fix bugs or add
features. To allow for this all post data is saved in the database, meaning the
index can be rebuilt from local data only.

`xapblr` uses semantic versioning and changes to indexing imply a minor version increase.
It is recommended to run `xapblr rebuild` after each minor version increase.


## Initialisation and rate-limiting

The Tumblr API is rate-limited to 1000 requests per hour and 5000 requests per
calendar day (EST). Since the `/posts` endpoint returns at most 20 posts per
requests initialising a large blog can easily take several hours, if not more
than a day. `xapblr index` automatically throttles to respect rate limits.

Incrementally fetching and indexing new posts is trivially cheap: the post
limit is 250 per day. Daily fetching therefore uses at most 13 requests, and
even hourly fetching is cheap.

However, continually reindexing an entire blog to reflect any edits that may
have been made is obviously prohibitively expensive. If you wish to update
posts that you know have been edited on Tumblr, pass suitable options to
`xapblr index`.

## Dependencies: ##
 * Python >= 3.11 and
 * * `xapian` Python bindings (from your distribution; not on PyPI)
 * * `pytumblr2`
 * * `dateparser`
 * * `requests`
 * * `sqlalchemy>=1.4`
 * * `flask` and `flask-assets` (optional, `web` extra, for the web interface)
 * * `pillow` and `open-clip-torch` (optional, `clip` extra, to generate and index captions for images)
 * * `humanfriendly` (optional, `humanfriendly` extra, for some nicer log messages)
 * `uwsgi` (optional, to serve the web interface)
 * `sass` and `pandoc` (optional, for the web interface)
