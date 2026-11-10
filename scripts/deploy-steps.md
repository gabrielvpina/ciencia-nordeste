Local:
git checkout main && git merge qualis && git push
./scripts/backup.sh
PACOTE=$(ls -t ~/Backups/ciencia-nordeste/ciencia-nordeste-backup-*.tar.gz | head -1)
scp -i ~/.ssh/SUA-CHAVE.pem "$PACOTE" ubuntu@3.215.184.253:~/

Server:
cd ~/ciencia-nordeste
git pull                                   # só desta vez: o script ainda não existe no servidor
./scripts/publicar.sh --sim ~/ciencia-nordeste-backup-*.tar.gz     # mostra o plano
./scripts/publicar.sh ~/ciencia-nordeste-backup-*.tar.gz           # publica código + dados do Qualis
Se houver mais de um backup na pasta do servidor, troque o * pelo nome do arquivo.
