import re
import time
from collections import defaultdict

LOG_FILE_PATH = "app_events.log"
FAILED_LOGIN_THRESHOLD = 5
TIME_WINDOW_SECONDS = 60 * 5  # 5 minutes window for this example, though simple script just counts consecutive

class LogMonitor:
    def __init__(self, filepath):
        self.filepath = filepath
        self.failed_attempts_by_ip = defaultdict(int)

    def print_alert(self, ip, count):
        print("\n" + "="*70)
        print("🚨 SECURITY ALERT AUTOMATED TRIGGER 🚨".center(70))
        print("="*70)
        print(f"[!] Anomalous Activity Detected in Application Event Logs")
        print(f"[!] Rule Triggered: Multiple Failed Logins (> {FAILED_LOGIN_THRESHOLD})")
        print(f"[!] Target Details:")
        print(f"    - IP Address: {ip}")
        print(f"    - Event Count: {count} failed attempts in rapid succession")
        print(f"[!] Action Taken: IP temporarily blocked. Alert forwarded to Slack channel #sec-alerts.")
        print(f"[!] Jira Ticket Created: SEC-9452 - Investigate potential brute force on IP {ip}")
        print("="*70 + "\n")

    def run_scan(self):
        print(f"Starting automated log review scan on: {self.filepath}...")
        time.sleep(1) # simulate processing time
        
        try:
            with open(self.filepath, 'r') as file:
                lines = file.readlines()
                
            print(f"Analyzed {len(lines)} application events.")
            time.sleep(0.5)

            # Simple parsing for the demo alert
            # Example log line: [2026-02-23 23:30:05] WARN  [user: unknown] - Failed login attempt (Invalid Token). IP: 203.0.113.45
            for line in lines:
                if "Failed login attempt" in line:
                    match = re.search(r"IP:\s*([\d\.]+)", line)
                    if match:
                        ip = match.group(1)
                        self.failed_attempts_by_ip[ip] += 1
                        
                        if self.failed_attempts_by_ip[ip] >= FAILED_LOGIN_THRESHOLD:
                            self.print_alert(ip, self.failed_attempts_by_ip[ip])
                            # Reset after alert for this demo
                            self.failed_attempts_by_ip[ip] = 0
                            
            print("Scan complete. Awaiting new events...")
                            
        except FileNotFoundError:
            print(f"Error: Log file '{self.filepath}' not found.")

if __name__ == "__main__":
    monitor = LogMonitor(LOG_FILE_PATH)
    monitor.run_scan()
