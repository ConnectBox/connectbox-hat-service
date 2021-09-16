# Branding file creation tool
  
import json

# Create the dictionary
details  = {'Brand':"ConnectBox", 'Image':"connectbox_image.png", 'Font':26,'pos_x': 7,'pos_y': 0}

# Write the dictionary
with open('brand.txt', 'w') as f:
    f.write(json.dumps(details))
    f.close()
