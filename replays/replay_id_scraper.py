import json
import lxml.html
import random
import requests
import sys
import time

BASE_URL = "https://ballchasing.com"

def get_header():
  with open("ballchasing-token.txt", "r", encoding="utf-8") as token_file:
    return { "Authorization": token_file.read() }
    
def get_replay_data(file_name):
  with open(file_name, "r") as replay_json:
    return json.load(replay_json)
    
def write_replay_data(file_name, json_data, indent=None):
  with open(file_name, "w") as replay_json:
    json.dump(json_data, replay_json, indent=indent)

# Recursively iterate through replay group to get replay ids
def get_replays(group_data, indent_level, team_code = None):
  res = requests.get(BASE_URL + group_data["id"])
  if res.status_code != 200:
    print(f"Exiting: Received {res.status_code}")
    return
    
  doc = lxml.html.fromstring(res.content)
  group_list = doc.xpath("//ul[@class='rgroups']/li/div[@class='main']")
  if len(group_list) == 0:
    # Group contains replays
    replay_list = doc.xpath("//ul[@class='creplays']//a[@class='replay-link']")
    for replay_elem in replay_list:
      replay_id = replay_elem.get("href").split("?g=")[0]
      print(('  ' * indent_level) + f'{replay_elem.text.strip()}: {replay_id}')
      matching_replays = [replay for replay in group_data["replays"] if replay["id"] == replay_id]
      if len(matching_replays) == 0:
        # Replay not seen before
        replay_obj = {
          "name": replay_elem.text.strip(),
          "id": replay_id
        }
        group_data["replays"].append(replay_obj)
        group_data["count"] += 1
  else:
    # Group contains child groups
    for group_elem in group_list:
      anchor = group_elem.xpath("div/h2/a")[0]
      group_id = anchor.get("href")
      if team_code is not None:
        if " vs " in anchor.text and team_code not in anchor.text:
          print(('  ' * indent_level) + f"Skipped {anchor.text}")
          continue
      print(('  ' * indent_level) + f'{anchor.text}: {group_id}')
      matching_groups = [child for child in group_data["children"] if child["id"] == group_id]
      if len(matching_groups) == 0:
        # Group not seen before
        child_group = {
          "name": anchor.text.replace(":", " -").replace("/", "-"),
          "id": group_id,
          "replays": [],
          "children": [],
          "count": 0,
          "downloaded": 0
        }
        group_data["children"].append(child_group)
      else:
        child_group = matching_groups[0]
        
      counts_elem = group_elem.xpath("div[@class='counts']/div")[1]
      if child_group["count"] != int(counts_elem.text.split(' ')[0]):
        # Subtract partial count before adding new count
        if len(matching_groups) != 0:
          group_data["count"] -= child_group["count"]
          
        time.sleep(random.uniform(1, 3.5))
        get_replays(child_group, indent_level + 1, team_code)
        group_data["count"] += child_group["count"]

def main():
  if len(sys.argv) == 1 or len(sys.argv) > 3:
    print(f"Usage: python replay_id_scraper.py [file_name] (team_code)")
    return 1
    
  file_name = sys.argv[1]
  team_code = None
  if len(sys.argv) == 3:
    team_code = sys.argv[2]
  
  replay_data = get_replay_data(file_name)
  try:
    for group in replay_data["groups"]:
      get_replays(group, 0, team_code)
  except BaseException as e:
    print(type(e), e)
  finally:
    write_replay_data(file_name, replay_data, indent=2)
  
  return 0

if __name__ == "__main__":
  main()