from joint_teapot import Canvas, Gitea


class Teapot:
    def __init__(self) -> None:
        self.canvas = Canvas()
        self.gitea = Gitea()


if __name__ == "__main__":
    teapot = Teapot()
