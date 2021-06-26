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
            repos = user.get('repos') if user.get('repos') else []
            repos_all_branches = user.get('repos_all_branches') if user.get('repos_all_branches') else []
            repos = set(repos + repos_all_branches)
            print("Found:", user.get('name', 'Unknow'), "total", len(repos), "projects")
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
@click.option('--host', help='The public IP of ES cluster.')
@click.option('--user', help='The user name of ES cluster.')
@click.option('--passwd', help='The user token of ES cluster.')
@click.argument('mode')
def _main(host, user, passwd, mode):
    if mode == "check":
        for proj in generate_projects():
            print(proj.get("name"), proj.get("user"), proj.get("repo"))
    elif mode == "import":
        _import(host, user, passwd)
    else:
        print("Unknow mode, only support 'check' and 'import'.")


def _import(host, user, passwd):
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
