"""AEGIS local research app. Run python app.py --help."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from core.service import ROOT, snapshot, review
_cache_setup_lock=threading.Lock()

def upgrade_cache(server):
    with _cache_setup_lock:
        cache=getattr(server,'upgrade_snapshot_cache',None)
        if cache is None:
            from dashboard.snapshot_cache import SnapshotCache
            cache=server.upgrade_snapshot_cache=SnapshotCache()
        return cache

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Only explicit public routes; no arbitrary filesystem or vault access.
        if self.headers.get('Host') not in {'127.0.0.1:'+str(self.server.server_port), 'localhost:'+str(self.server.server_port)}:
            self.send_error(403); return
        route = self.path.split('?')[0]
        if route == '/healthz':
            # A bounded local probe does not run strategy/provider code or inspect
            # private position ledgers. It must not recursively probe itself.
            from ops.supervisor import status
            payload = json.dumps(status(probe=False), allow_nan=False).encode(); kind = 'application/json'
        elif route == '/api/upgrade':
            # Heavy study summaries refresh once in the background. Every
            # response rechecks original quote/receipt/expiry timestamps.
            payload = json.dumps(upgrade_cache(self.server).get(), allow_nan=False).encode(); kind = 'application/json'
        elif route == '/api/status':
            from core.spy_research import current
            payload = json.dumps(current()).encode(); kind = 'application/json'
        elif route == '/':
            payload = (ROOT/'dashboard/upgrade.html').read_bytes(); kind = 'text/html; charset=utf-8'
        else:
            self.send_error(404); return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(payload)
    def log_message(self, *args):
        pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    server = sub.add_parser('serve'); server.add_argument('--port', type=int, default=8767)
    sub.add_parser('status'); sub.add_parser('review')
    evaluate = sub.add_parser('evaluate'); evaluate.add_argument('input')
    args = parser.parse_args()
    if args.command == 'serve':
        print(f'AEGIS dashboard: http://127.0.0.1:{args.port}', flush=True)
        ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
    elif args.command == 'evaluate':
        from core.proposals import evaluate_file
        print(json.dumps(evaluate_file(args.input), indent=2))
    else:
        print(json.dumps(review() if args.command == 'review' else snapshot(), indent=2))

if __name__ == '__main__': main()
