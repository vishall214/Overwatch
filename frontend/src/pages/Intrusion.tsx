import { Navigate } from "react-router-dom";

export default function Intrusion() {
  return <Navigate to="/monitor?module=intrusion" replace />;
}
