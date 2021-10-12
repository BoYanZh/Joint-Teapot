import glob
import ntpath

from joint_teapot import Teapot, logger


class MyTeapot(Teapot):
    def ve482p1(self) -> None:
        for repo_name in self.gitea.get_all_repo_names():
            if not repo_name.endswith("p1"):
                continue
            faults = []
            succeed = self.checkout_to_repo_by_release_name(repo_name, "p1")
            if succeed:
                contain_c_file = False
                contain_readme_file = False
                for fn in glob.glob(f"{self.git.repos_dir}/{repo_name}/*.*"):
                    basename = ntpath.basename(fn)
                    if basename.endswith(".c"):
                        contain_c_file = True
                    if basename.lower().startswith("readme"):
                        contain_readme_file = True
                if not contain_c_file:
                    faults.append(
                        "no C file found in root directory in release p1, "
                        "can not compile on JOJ"
                    )
                if not contain_readme_file:
                    faults.append(
                        "no README file found in root directory in release p1"
                    )
            else:
                faults.append("no release named p1")
            if faults:
                fault_string = ""
                for fault in faults:
                    fault_string += f"- {fault}\n"
                logger.info("\n".join(("", repo_name, "", fault_string)))
                self.gitea.issue_api.issue_create_issue(
                    self.gitea.org_name,
                    repo_name,
                    body={
                        "body": fault_string,
                        "title": "p1 submission pre-check failed",
                    },
                )


if __name__ == "__main__":
    teapot = MyTeapot()
    teapot.ve482p1()
