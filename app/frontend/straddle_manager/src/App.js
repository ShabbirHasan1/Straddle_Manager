import logo from './logo.svg';
import './App.css';


function TopBar(){
  return (
    <div>
      Trading Terminal
    </div>
  )
}

function Form(){
  return (
    <form>
      <label>Email:</label><br/>
      <input type="text"/><br/>
      <label>Password:</label><br/>
      <input type="password"/><br/>
      <input type="submit" value="Login"/>
    </form>
  )
}

function App() {
  return (
    <div>
      <TopBar/> <br/>
      <Form/>
    </div>
  );
}

export default App;
