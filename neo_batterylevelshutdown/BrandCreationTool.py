# Branding file creation tool
import io  
import json
import 'connectbox-pi/ansible/group_vars/brand'

# not that Enable_MassStorage of 1 will override g_device.  Additionally, both MassStorage and g_device are subject to otg : high, low, none

# Create the dictionary
details  = {'Brand':"{{ connectbox_default_hostname }}", \
        'Image':"{{ lcd_logo }}", \
        'enhanced_logo': "{{ enhanced_interface_logo }}", \
        'Font':{{ lcd_font_size }}, \
        'pos_x': {{ lcd_x_position}}, \
        'pos_y': {{ lcd_y_position}}, \

        "usb0NoMount": {{ usb0NoMount }}, \

        "otg_enable": {{ lcd_otg_enable }}\
        'g_device': "{{lcd_g_device}}", "otg": {{ otg_enable }}, \
        'Enable_MassStorage':{{enable_mass_storage}}, \

        "Screen_Enable": [
        {{ lcd_pages_main }},
        {{ lcd_pages_info }},
        {{ lcd_pages_battery }},
        {{ lcd_pages_multi_bat }},
        {{ lcd_pages_memory }},
        {{ lcd_pages_stats_hour_one }},
        {{ lcd_pages_stats_hour_two }},
        {{ lcd_pages_stats_day_one }},
        {{ lcd_pages_stats_day_two }},
        {{ lcd_pages_stats_week_one }},
        {{ lcd_pages_stats_week_two }},
        {{ lcd_pages_stats_month_one }},
        {{ lcd_pages_stats_month_two }},
        {{ lcd_pages_admin }}
        ], \

        "server_url": "{{ server_url }}", \
        "server_authorization": "{{ server_authorization }}", \
        "server_sitename": "{{ server_sitename }}", \
        "server_siteadmin_name": "{{ server_siteadmin_name }}", \
        "server_siteadmin_email": "{{ server_siteadmin_email }}", \
        "server_siteadmin_phone": "{{ server_siteadmin_phone }}"
        }

# Write the dictionary
with io.open('brand.txt', mode='w') as f:
    f.write(json.dumps(details))
    f.close()

with open('hostname', 'w') as f:
    f.write((details["Brand"]).lower()) 
    f.close()

