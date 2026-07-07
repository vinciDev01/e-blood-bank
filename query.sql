SELECT * FROM ebloodbank._auth_customuser;

UPDATE ebloodbank._auth_customuser
SET password='pbkdf2_sha256$1200000$lAC6ygOjHnnm8UOEwL7rYb$yNf1Z9j7r99+aoV5bUi/RDKip1/YkdAkfPDLjfN8Nck='
WHERE id = 5;

UPDATE ebloodbank._auth_customuser
SET email='titipostephanie79@gmail.com'
WHERE id=5;

                titipostephanie219@gmail.com
                titipostephanie79@gmail.com
                
  SELECT u.email, u.role, d.nom, d.prenom, d.groupe_sanguin                                                              
  FROM _auth_customuser u                                                                                                
  JOIN _auth_donneur d ON d.user_id = u.id;
  
  