function togglePassword(){
  const pw = document.getElementById('password');
  const t = document.querySelector('.toggle');
  if(pw.type === 'password'){ pw.type = 'text'; t.textContent = 'Hide'; }
  else { pw.type = 'password'; t.textContent = 'Show'; }
}

function handleLogin(e){
  e.preventDefault();
  const u = document.getElementById('username').value;
  const p = document.getElementById('password').value;
  // Demo validation
  if(u === 'admin' && p === 'password123'){
    alert('Login successful!');
    // window.location = 'dashboard.html';
  } else {
    document.getElementById('msg').textContent = 'Incorrect username or password';
  }
}
