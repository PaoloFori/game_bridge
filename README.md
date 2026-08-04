# game_bridge

ROS2 node that bridges a decision/controller node to an external game server,
translating high-level game commands published on a ROS2 topic into the
game's own wire protocol.

Currently targets the [Cortical Peaks Challenge 2026](https://github.com/neuroTUM/cortical-peaks-challenge-2026)
BCI/game protocol (UDP), with support for pointing the connection at either a
local instance of the game server or the official competition server.

See branches for protocol-specific implementations.

## `game_bridge` package (this branch)

An `ament_python` ROS2 package with a single node, `game_bridge_node`:

- **Subscribes** to a command topic (default `/game/command`, `std_msgs/String`
  with content `INPUT_A`/`INPUT_B`/`INPUT_C`/`INPUT_D`) published by a
  separate controller node. This node has no game/BCI decision logic of its
  own -- it only forwards already-decided commands.
- **Registers and maintains a session** with the game server per
  [`PROTOCOL.md`](https://github.com/neuroTUM/cortical-peaks-challenge-2026/blob/main/PROTOCOL.md)
  (REGISTER/ACK, bidirectional PING/PONG heartbeat, automatic re-registration
  on timeout).
- **Publishes connection status** on `~/status` (`connected`/`disconnected`).

Note: a BCI-role client never receives game state (countdown/game_over) from
the server -- that's spectator-only per the protocol. If the controller needs
that, this node would additionally need a spectator-role connection, not yet
implemented here.

### Parameters

| Parameter        | Default            | Description                              |
| ----------------- | ------------------- | ----------------------------------------- |
| `server_host`     | `127.0.0.1`          | Game server host/IP                       |
| `server_port`     | `5000`               | Game server UDP port                      |
| `display_name`    | `game_bridge-<host>` | Name shown in the server UI               |
| `command_topic`   | `/game/command`      | Topic to subscribe to for game commands   |

### Running

```bash
ros2 launch game_bridge bridge.launch.py target:=local   # 127.0.0.1:5000
ros2 launch game_bridge bridge.launch.py target:=tum     # config/tum.yaml
```

`config/tum.yaml` still has a placeholder host -- fill it in once the
organizers publish the competition server address.
