# Branding file creation tool
import io  
import json

# Create the dictionary
details  = {'Brand':"ConnectBox", 'Image':"connectbox_logo.png", \
        'Font':26,'pos_x': 7,'pos_y': 0, \
        'Enable_MassStorage': 0, 'Screen_Enable': [1,1,1,1,1,1,1,1,1,1,1,1,1],  \
        'g_device': "g_serial"}

# Write the dictionary
with io.open('brand.txt', mode='w') as f:
    f.write(json.dumps(details))
    f.close()

with open('hostname', 'w') as f:
    f.write((details["Brand"]).lower()) 
    f.close()

