UPDATE service.backups
SET path = replace(path, '.pdf', '')
WHERE path LIKE '%.pdf';
