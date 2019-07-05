# FaaS-based STM

This is a small library that attempts to do STM to update stored
state in an object-storage system.

It also interacts with the Slack API.

The whole thing works by saving external effects until the
STM commit passes; at that point, the external effects are
committed also.

