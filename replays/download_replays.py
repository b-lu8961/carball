import json
import os
import random
import requests
import sys
import time

DOWNLOAD_URL = "https://ballchasing.com/api/replays/{}/file"
failed_ids = []

def get_header():
  with open("ballchasing-token.txt", "r", encoding="utf-8") as token_file:
    return { "Authorization": token_file.read() }

def get_replay_data(file_name):
  with open(file_name, "r") as replay_json:
    return json.load(replay_json)
    
def write_replay_data(file_name, json_data, indent=None):
  with open(file_name, "w") as replay_json:
    json.dump(json_data, replay_json, indent=indent)

def download(group_data, base_path):
  header = get_header()
  dir_path = os.path.join(base_path, group_data['name'])
  dir_list = os.listdir() if base_path == '' else os.listdir(base_path)
  if group_data['name'] not in dir_list:
    os.mkdir(dir_path)
  if (len(group_data['replays']) != 0) and (group_data['count'] != group_data['downloaded']):
    group_data['downloaded'] = 0
    for replay in group_data['replays']:
      replay_id = replay['id'].split('/')[-1]
      #print(DOWNLOAD_URL.format(replay_id))
      req_url = DOWNLOAD_URL.format(replay_id)
      res = requests.get(req_url, headers=header)
      if res.ok:
        replay_name = replay['name'] + '.replay'
        replay_path = os.path.join(dir_path, replay_name)
        replay_path = replay_path.replace("/", "_")
        with open(replay_path, 'wb') as replay_file:
          replay_file.write(res.content)
        print(replay_path)
        group_data['downloaded'] += 1
        time.sleep(2)
      else:
        print(f"Status Code {res.status_code} for url:\n {req_url}")
        failed_ids.append(req_url)
        time.sleep(10)
  else:
    for child_group in group_data['children']:
      if child_group['count'] != child_group['downloaded']:
        group_data['downloaded'] -= child_group['downloaded']
        download(child_group, dir_path)
        group_data['downloaded'] += child_group['downloaded']
        print(child_group['downloaded'])
  

def main():
  if len(sys.argv) == 1:
    print(f"Usage: python download_replays.py [file_name]")
    return 1
    
  file_name = sys.argv[1]
  replay_data = get_replay_data(file_name)
  try:
    for group in replay_data["groups"]:
      download(group, '')
    for name in failed_ids:
      print(name)
    write_replay_data(file_name, replay_data, indent=2)
  except BaseException as e:
    print(type(e), e)

if __name__ == "__main__":
  main()