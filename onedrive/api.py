import json
import os
import os.path
import requests
import urllib.parse

base_url = 'https://api.onedrive.com/v1.0'

def exists(file, auth):
    code = requests.get(base_url + "/drive/root:" + file, headers=auth).status_code
    return code == 200


def get_metadata(file, auth):
    """
    get the metadata for the given path: https://dev.onedrive.com/items/get.htm
    :param file:
    :param auth:
    :return: :rtype: Result with code 200 + json if all is okay
    """
    res = requests.get(base_url+"/drive/root:" + file, headers=auth)
    return Result(res)


def mkdir(new_dir, auth, parents=False):
    """
    creates the directory structure (compare mkdir)
    https://dev.onedrive.com/items/create.htm
    :param new_dir:
    :param auth:
    :param parents: true if parents should be created (cmp: mkdir -p)
    :return: Result with code 201 + json if dir created
    """
    dirname = os.path.basename(new_dir)
    headers = dict(auth)
    headers['Content-Type'] = 'application/json'
    data = json.dumps({
        "name": dirname,
        "folder": {}
    })

    # make dir. This somehow only works with the ID. So get the ID before.
    parent = os.path.dirname(new_dir)
    parent_meta = get_metadata(file=parent, auth=auth)

    if parent_meta.status_code == 404 and parents:  # parent does not exist but should be created!
        mkdir(parent, auth, True)  # recurse into parents
        parent_meta = get_metadata(file=parent, auth=auth)

    parent_id = dict(parent_meta.json_body()).get('id', '00000000')
    res = requests.post(base_url+"/drive/items/"+parent_id+"/children", headers=headers, data=data)
    return Result(res)


def delete(file, auth):
    return Result(requests.delete(base_url+"/drive/root:"+file, headers=auth))


def get_sha1(file, auth):
    m = get_metadata(file, auth).json_body()
    return m.get('file', {}).get('hashes', {}).get('sha1Hash')


def is_file_meta(meta):
    return 'file' in meta


def is_dir_meta(meta):
    return 'folder' in meta


def copy(src, dst, auth):
    """Copy a onedrive file
    :param src:
    :param dst:
    :param auth:
    :return: URL for a AsyncJobStatus in LOCATION header with code 202
    """
    header = dict(auth)
    header['Content-Type'] = 'application/json'
    header['Prefer'] = 'respond-async'

    dst_path, dst_file = os.path.split(dst)
    dst_path = dst_path[1:]  # remove the leading slash
    data = json.dumps({
      "parentReference": {
        "path": "/drive/root:" + dst_path
      },
      "name": dst_file
    })

    copy_request = requests.post(base_url+'/drive/root:'+src+':/action.copy', headers=header, data=data)
    return Result(copy_request)


def upload_simple(data, dst, auth, conflict="replace"):
    """ Simple item upload is available for items with less than 100MB of content.
    see: https://dev.onedrive.com/items/upload.htm
    :param data: binary stream of data
    :param dst: upload path
    :param auth: auth header
    :param conflict: fail, replace, or rename. The default for PUT is replace
    :return: 201 Created
    """
    url = base_url + "/drive/root:" + dst + ":/content?conflictBehavior="+conflict
    requ = requests.put(url, data=data, headers=auth)
    return Result(requ)


class Result:

    def __init__(self, response):
        self.status_code = response.status_code
        self.text = response.text
        self.headers = response.headers

    def json_body(self):
        return json.loads(self.text)

    def to_string(self):
        str_header = "\n\t".join([str(k)+":"+str(v) for k,v in self.headers.items()])
        return """
status_code: {code},
headers:
    {headers}
text: {text}""".format(code=self.status_code,
                       headers=str_header,
                       text=json.dumps(self.json_body(), indent=2))