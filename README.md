# game_bridge

ROS2 node that bridges a decision/controller node to an external game server,
translating high-level game commands published on a ROS2 topic into the
game's own wire protocol.

Currently targets the [Cortical Peaks Challenge 2026](https://github.com/neuroTUM/cortical-peaks-challenge-2026)
BCI/game protocol (UDP), with support for pointing the connection at either a
local instance of the game server or the official competition server.

See branches for protocol-specific implementations.
