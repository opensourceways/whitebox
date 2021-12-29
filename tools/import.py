import time
import sys

import click
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk
import yaml


def _get_user_id(user, repo):
    user_name = user.get('name', 'Unknow')
    user_id = ''
    if 'gitee.com' in repo:
        user_id = user.get('gitee_id', '')
    elif 'github.com' in repo:
        user_id = user.get('github_id', '')
    elif 'gitlab.com' in repo:
        user_id = user.get('gitlab_id', '')
    if not user_id:
        print("ERROR: Can't load the (%s) user id, "
              "Pls specify %s (gitee|github|gitlab)_id." % (user_name, repo))
        sys.exit(1)
    return user_id


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
                user_id = _get_user_id(user, repo)
                doc = {
                    "name": user.get('name', 'Unknow'),
                    "user": user_id,
                    "repo": repo,
                    "created_at": time.strftime("%Y-%m-%dT%H:00:00+0800")
                }
                yield doc


def generate_users():
    with open("./data.yml") as f:
        x = yaml.load(f, Loader=yaml.FullLoader)
        users = x.get("users")
        for user in users:
            name = user.get('name', '')
            gitee_id = user.get('gitee_id', '')
            github_id = user.get('github_id', '')
            gitlab_id = user.get('gitlab_id', '')
            alias = [x for x in user.get('alias', [])]
            alias += [gitee_id, github_id, gitlab_id, name]
            names = set(x for x in alias if x)
            for name in names:
                doc = {
                    "name": user.get('name'),
                    "alias": name,
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
        for name in generate_users():
            print(name.get("name"), name.get("alias"))
    elif mode == "import":
        _import(host, user, passwd)
    else:
        print("Unknow mode, only support 'check' and 'import'.")


def _bulk(es, index, iter):
    es.indices.delete(index=index, ignore=[404])
    actions = streaming_bulk(
        client=es, index=index, actions=iter
    )
    for ok, action in actions:
        if not ok:
            print("Failed to insert doc...")


def _import(host, user, passwd):
    es = Elasticsearch([host], http_auth=(user, passwd), use_ssl=True, verify_certs=False)

    _bulk(es, 'whitebox_projects', generate_projects())
    _bulk(es, 'whitebox_users', generate_users())

    print("Load complete.")


if __name__ == "__main__":
    _main()
