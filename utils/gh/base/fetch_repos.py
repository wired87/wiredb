import os
from urllib.parse import urlparse

import requests
from git import Repo

class GitHub:

    def __init__(self, urls, clone_dest, token=None):
        self.urls = urls
        self.clone_dest=clone_dest

        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})

    def clone_repos_from_urls(self):
        local_dirs = []

        for url in self.urls:
            repo_name = os.path.splitext(os.path.basename(urlparse(url).path))[0]
            local_path = os.path.join(self.clone_dest, repo_name)
            if not os.path.exists(local_path):
                Repo.clone_from(url, local_path)
            local_dirs.append((repo_name, url))
        return local_dirs