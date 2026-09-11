"""Narrow, reversible file-limit patch for the existing Cloud chat server.

Never replaces the server with an archived version, opens a database, changes
accounts or runs the full installer. Run only on the existing Cloud host.
"""
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import time
import urllib.request

HOST = '5.42.102.11'
PIN = 'a84186ad26b22e7d69f23d1838a9db5a2b277a6d567d6e49249c7714153e5d4a'
LIMIT = 419686400  # 400 MiB of plaintext, including authenticated record overhead.


EDIT_VALIDATION = """  if op=='edit':
   if DB.execute('SELECT author FROM posts WHERE mid=?',(target,)).fetchone()!=(nick,):raise Problem(403,'Изменить сообщение может только автор')
   previous=DB.execute('SELECT body FROM channel_history WHERE mid=? AND room=?',(target,rid)).fetchone()
   if not previous:raise Problem(404,'Исходное сообщение ещё не сохранено')
   original=json.loads(open_channel_record(rid,target,previous[0])['record'])['payload']
   if original.get('kind') not in ('text','file') or any(k in original for k in ('mini','mini_update','watch')) or original.get('custom_sticker'):raise Problem(400,'Это сообщение нельзя редактировать')
   if not isinstance(body.get('text'),str) or len(body['text'].encode())>10000 or original['kind']=='text' and not body['text'].strip():raise Problem(400,'Неверный текст правки')
   if type(body.get('edit_version')) is not int or not 1<=body['edit_version']<=record['time']+300000 or not isinstance(body.get('edit_id'),str) or not re.fullmatch('[a-f0-9-]{36}',body['edit_id']):raise Problem(400,'Неверная версия правки')
"""


def patch_source(source):
    tree = ast.parse(source)
    limits = [n.body for n in ast.walk(tree)
              if isinstance(n, ast.IfExp)
              and isinstance(n.test, ast.Compare)
              and ast.dump(n.test) == ast.dump(ast.parse("kind == 'blob'", mode='eval').body)
              and isinstance(n.body, ast.Constant) and type(n.body.value) is int]
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == 'store_channel_history']
    if len(limits) != 1 or len(functions) != 1:
        raise ValueError('Неизвестная структура сервера. Код не изменён.')
    fields = [n.value for n in ast.walk(functions[0]) if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'fields' for t in n.targets)
              and isinstance(n.value, ast.Set)]
    if len(fields) != 1 or not all(isinstance(n, ast.Constant) and isinstance(n.value, str)
                                   for n in fields[0].elts):
        raise ValueError('Неизвестный формат вложений. Код не изменён.')
    lines = source.encode().splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    def span(node):
        return offsets[node.lineno - 1] + node.col_offset, offsets[node.end_lineno - 1] + node.end_col_offset
    edits = []
    limit = limits[0]
    if limit.value < LIMIT:
        if limit.value != 26214416:
            raise ValueError('Неизвестный исходный лимит. Код не изменён.')
        edits.append((*span(limit), str(LIMIT).encode()))
    existing = {n.value for n in fields[0].elts}
    if not {'cloud_blob', 'blob_key', 'blob_iv'}.issubset(existing):
        raise ValueError('Сервер ещё не поддерживает зашифрованные вложения.')
    missing = {'blob_format', 'document', 'edit_version', 'edit_id'} - existing
    if missing:
        start, end = span(fields[0])
        before = source.encode()[start:end]
        edits.append((start, end, before[:-1] + b',' + ','.join(repr(f) for f in sorted(missing)).encode() + b'}'))
    # Add one control operation without replacing the server or touching storage schema.
    for variable, required in [('op', {'reaction', 'pin', 'unpin'}),
                               ('action', {'publish', 'reaction', 'pin', 'unpin', 'signal', 'comment'})]:
        checks = [n.comparators[0] for n in ast.walk(tree)
                  if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name)
                  and n.left.id == variable and len(n.ops) == 1 and isinstance(n.ops[0], ast.NotIn)
                  and isinstance(n.comparators[0], ast.Tuple)]
        matches = [n for n in checks if required.issubset({x.value for x in n.elts if isinstance(x, ast.Constant)})]
        if len(matches) != 1:
            raise ValueError('Неизвестная проверка действий. Код не изменён.')
        node = matches[0]
        if 'edit' not in {x.value for x in node.elts if isinstance(x, ast.Constant)}:
            start, end = span(node)
            edits.append((start, end, source.encode()[start:end - 1] + b",'edit')"))
    controls = [n for n in ast.walk(functions[0]) if isinstance(n, ast.If)
                and ast.dump(n.test) == ast.dump(ast.parse("body['kind'] == 'control'", mode='eval').body)]
    if len(controls) != 1:
        raise ValueError('Неизвестная обработка правок. Код не изменён.')
    control = controls[0]
    edit_checks = [n for n in control.body if isinstance(n, ast.If)
                   and ast.dump(n.test) == ast.dump(ast.parse("op == 'edit'", mode='eval').body)]
    if edit_checks:
        if len(edit_checks) != 1 or ast.dump(edit_checks[0]) != ast.dump(ast.parse(EDIT_VALIDATION.strip().replace('\n   ', '\n ')).body[0]):
            raise ValueError('На сервере другая обработка правок. Код не изменён.')
    else:
        insertion = offsets[control.body[-1].end_lineno]
        edits.append((insertion, insertion, EDIT_VALIDATION.encode()))
    result = source.encode()
    for start, end, replacement in sorted(edits, reverse=True):
        result = result[:start] + replacement + result[end:]
    text = result.decode()
    compile(text, 'server.py', 'exec')  # Parse only; never import or execute the service here.
    return text


def install_patch(path, backup, restart_and_verify):
    path, backup = Path(path), Path(backup)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Неожиданный путь сервера.')
    original = path.read_text()
    patched = patch_source(original)
    if patched == original:
        return False
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    shutil.copy2(path, backup / 'server.py')
    fd, temporary = tempfile.mkstemp(prefix='.oldi-limit-', dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(patched)
            stream.flush()
            os.fsync(stream.fileno())
        status = path.stat()
        os.chmod(temporary, status.st_mode & 0o777)
        os.chown(temporary, status.st_uid, status.st_gid)
        if path.read_text() != original:
            raise ValueError('Код изменён другим процессом. Попробуйте позже.')
        os.replace(temporary, path)
        try:
            restart_and_verify()
        except Exception:
            shutil.copy2(path, backup / 'failed-server.py')
            shutil.copy2(backup / 'server.py', temporary)
            os.replace(temporary, path)
            restart_and_verify()
            raise
        return True
    finally:
        temporary.unlink(missing_ok=True)


def main():
    if os.geteuid() != 0 or HOST not in subprocess.check_output(['hostname', '-I'], text=True).split():
        raise ValueError('Нужен root на старом Cloud 5.42.102.11. На Aéza запускать не нужно.')
    certificate = Path('/etc/oldy-chat/server.crt')
    if hashlib.sha256(ssl.PEM_cert_to_DER_cert(certificate.read_text())).hexdigest() != PIN:
        raise ValueError('Сертификат Cloud не совпадает. Код не изменён.')
    context = ssl.create_default_context(cafile=str(certificate))
    path = Path('/opt/oldy-chat/server.py')
    service = subprocess.check_output(['systemctl', 'show', 'oldy-chat', '--property=ExecStart', '--value'], text=True)
    if str(path) not in service:
        raise ValueError('Служба использует другой путь. Код не изменён.')
    def health():
        with urllib.request.urlopen('https://' + HOST + '/health', context=context, timeout=5) as response:
            if response.status != 200 or json.load(response).get('service') != 'oldy-chat':
                raise ValueError('Сервер не прошёл проверку соединения.')
    def restart():
        subprocess.run(['systemctl', 'restart', 'oldy-chat'], check=True)
        until = time.monotonic() + 25
        while True:
            try:
                health()
                return
            except Exception:
                if time.monotonic() >= until:
                    raise
                time.sleep(1)
    health()
    with open('/var/lock/oldy-update.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        backup = Path('/var/lib/oldy-chat/update-backups') / ('files-400-' + str(time.time_ns()))
        changed = install_patch(path, backup, restart)
    print('Cloud поддерживает файлы до 400 МБ и редактирование сообщений. Аккаунты и история сохранены.')
    if changed:
        print('Предыдущий код: ' + str(backup / 'server.py'))


if __name__ == '__main__':
    main()
