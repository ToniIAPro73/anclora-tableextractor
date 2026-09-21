# Auth-Gated App Testing Playbook (Emergent Google Auth)

## Step 1: Create Test User & Session in MongoDB (DB: test_database)
```
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({ user_id: userId, email: 'test.user.'+Date.now()+'@example.com', name: 'Test User', picture: 'https://via.placeholder.com/150', created_at: new Date().toISOString() });
db.user_sessions.insertOne({ user_id: userId, session_token: sessionToken, expires_at: new Date(Date.now()+7*24*60*60*1000).toISOString(), created_at: new Date().toISOString() });
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Backend API
```
curl -X GET "$URL/api/auth/me" -H "Authorization: Bearer $TOKEN"
curl -X POST "$URL/api/documents/upload?lang=es" -H "Authorization: Bearer $TOKEN" -F "files=@/tmp/sample_invoice.pdf"
curl -X GET "$URL/api/documents" -H "Authorization: Bearer $TOKEN"
```

## Step 3: Browser Testing
```
await page.context.add_cookies([{ "name":"session_token","value": TOKEN, "domain": DOMAIN, "path":"/", "httpOnly":true, "secure":true, "sameSite":"None" }])
await page.goto(URL + "/upload")
```

## Notes
- Callback detection uses useLocation().hash, not window.location.hash.
- All Mongo queries use {"_id": 0} projection.
- Sessions stored with ISO string expires_at (timezone-aware compare in backend).
