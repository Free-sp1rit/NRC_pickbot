Put screenshot templates in this folder.

Example config step:

{
  "type": "wait_image",
  "template": "templates/battle_ready.png",
  "region": [100, 100, 300, 200],
  "threshold": 0.92,
  "timeout_seconds": 5.0,
  "relative_to_window": true
}
