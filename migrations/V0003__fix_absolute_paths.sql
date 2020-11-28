UPDATE service.backups
SET path = replace(path, '/mnt/raid/Yandex Disk/HDA/', '')
WHERE path LIKE '/mnt/raid/Yandex Disk/HDA/%';
