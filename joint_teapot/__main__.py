from joint_teapot import Canvas, Gitea

__version__ = "0.0.0"


class Teapot:
    def __init__(self) -> None:
        self.canvas = Canvas()
        self.gitea = Gitea()


if __name__ == "__main__":
    teapot = Teapot()
