from setuptools import find_packages, setup

package_name = "game_bridge"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/bridge.launch.py"]),
        (f"share/{package_name}/config", ["config/local.yaml", "config/tum.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Paolo",
    maintainer_email="forin.paolo98@gmail.com",
    description="ROS2 bridge connecting a controller node to the Cortical Peaks Challenge 2026 game server.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "game_bridge_node = game_bridge.bridge_node:main",
        ],
    },
)
