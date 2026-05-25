from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'tbot3_nav_monitor'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*')),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='domenico.quartodipalo@mail.polimi.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
             'recovery_monitor_node = tbot3_nav_monitor.recovery_monitor_node:main',
             'adaptive_behavior_node = tbot3_nav_monitor.adaptive_behavior_node:main',
             'velocity_adapter_node = tbot3_nav_monitor.velocity_adapter_node:main',
             'goal_tolerance_adapter_node = tbot3_nav_monitor.goal_tolerance_adapter_node:main',
             'real_time_monitor_node = tbot3_nav_monitor.real_time_monitor_node:main',
             'fake_battery_node = tbot3_nav_monitor.fake_battery_node:main',
             'csv_logger_node = tbot3_nav_monitor.csv_logger_node:main'
        ],
    },
)
