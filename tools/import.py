import time

import click
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk
import yaml


def generate_projects():
    with open("./data.yml") as f:
        x = yaml.load(f, Loader=yaml.FullLoader)
        users = x.get("users")
        for user in users:
            repos = set(user.get('repos', []) + user.get('repos_all_branches', []))
            print("Import:", user.get('name', 'Unknow'), "total", len(repos), "projects")
            for repo in repos:
                gitee_user = user.get('gitee_id', 'Unknow')
                github_user = user.get('github_id', 'Unknow')
                doc = {
                    "name": user.get('name', 'Unknow'),
                    "user": gitee_user if 'gitee.com' in repo else github_user,
                    "repo": repo,
                    "created_at": time.strftime("%Y-%m-%dT%H:00:00+0800")
                }
                yield doc


@click.command()
@click.option('--host')
@click.option('--user')
@click.option('--passwd')
def _main(host, user, passwd):
    es = Elasticsearch([host], http_auth=(user, passwd), use_ssl=True, verify_certs=False)
    # Cleanup es index
    es.indices.delete(index='whitebox_projects', ignore=[404])

    actions = streaming_bulk(
        client=es, index="whitebox_projects", actions=generate_projects()
    )
    for ok, action in actions:
        if not ok:
            print("Failed to insert doc...")
    print("Load complete.")


if __name__ == "__main__":
    _main()
