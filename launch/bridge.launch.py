"""Launch game_bridge against either the local or the TUM game server.

Usage:
    ros2 launch game_bridge bridge.launch.py target:=local
    ros2 launch game_bridge bridge.launch.py target:=tum
"""

from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.launch_context import LaunchContext
from launch.launch_description_entity import LaunchDescriptionEntity
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

VALID_TARGETS = ("local", "tum")


def _launch_setup(context: LaunchContext, *_args: object, **_kwargs: object) -> list[LaunchDescriptionEntity]:
    target = LaunchConfiguration("target").perform(context)
    if target not in VALID_TARGETS:
        msg = f"Unknown target '{target}', expected one of {VALID_TARGETS}"
        raise RuntimeError(msg)

    params_file = os.path.join(get_package_share_directory("game_bridge"), "config", f"{target}.yaml")

    return [
        Node(
            package="game_bridge",
            executable="game_bridge_node",
            name="game_bridge",
            output="screen",
            parameters=[params_file],
        )
    ]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "target",
                default_value="local",
                description="Which server to connect to: 'local' or 'tum'.",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
