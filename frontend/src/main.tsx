import ReactDOM from "react-dom/client";
import App from "./App";
import { useStudio } from "./state/store";
import "./styles.css";

if (import.meta.env.DEV) {
  (window as any).studio = useStudio;
}

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
