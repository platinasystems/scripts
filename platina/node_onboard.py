import ansible_runner
import urllib3

from .node import Node

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NodeOnboard(Node):
    def __init__(self, session_token=None, config: dict = None, managed: bool = False):
        self.session_token = session_token
        self.config = config or {}

    def onboard(self, ips, ssh_user, ssh_pwd, managed):
        import concurrent.futures
        ips = self.parse_ip_list(ips)

        def onboard_single(ip):
            print(f"Adding the node with IP {ip} to PCC...")
            try:
                self.onboard_node(ip=ip, ssh_user=ssh_user, password=ssh_pwd, managed=managed)
            except RuntimeError as e:
                print(f"❌ Failed to onboard node {ip}: {e}")
            else:
                print(f"✅ Node {ip} onboarded successfully.")

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(onboard_single, ips)


    def onboard_node(self, ip: str, ssh_user: str, password: str, managed: bool = False):

        if managed:
            extravars = {
                "ansible_user": ssh_user,
                "ansible_host": ip,
                "ansible_password": password,
                "ansible_become_password": password,
                "user_to_add": 'pcc',
                "ansible_ssh_common_args": "-o StrictHostKeyChecking=no"
            }

            result = ansible_runner.run(
                private_data_dir=".",  # runner still needs a dir for internal logs
                playbook="platina/playbooks/onboard_node.yml",
                inventory=f"{ip},",
                extravars=extravars,
                quiet=True
            )

            if result.rc != 0:
                stdout_content = result.stdout.read() if hasattr(result.stdout, "read") else str(result.stdout)
                raise RuntimeError(
                    f"Playbook failed:\n"
                    f"Status: {result.status}\n"
                    f"RC: {result.rc}\n"
                    f"STDOUT:\n{stdout_content}"
                )

            ssh_user = ""

        self.add_node(ip=ip, managed=managed, admin_user=ssh_user)
        print(f"Node added to PCC successfully with IP {ip}.")
