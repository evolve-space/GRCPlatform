import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { PanelPage } from "./pages/PanelPage";
import { ActionDetailPage } from "./pages/actions/ActionDetailPage";
import { ActionFormPage } from "./pages/actions/ActionFormPage";
import { ActionsListPage } from "./pages/actions/ActionsListPage";
import { AssetDetailPage } from "./pages/assets/AssetDetailPage";
import { AssetFormPage } from "./pages/assets/AssetFormPage";
import { AssetsListPage } from "./pages/assets/AssetsListPage";
import { ControlDetailPage } from "./pages/controls/ControlDetailPage";
import { ControlFormPage } from "./pages/controls/ControlFormPage";
import { ControlsListPage } from "./pages/controls/ControlsListPage";
import { EvidenceDetailPage } from "./pages/evidence/EvidenceDetailPage";
import { EvidenceEditPage } from "./pages/evidence/EvidenceEditPage";
import { EvidenceListPage } from "./pages/evidence/EvidenceListPage";
import { EvidenceUploadPage } from "./pages/evidence/EvidenceUploadPage";
import { FindingDetailPage } from "./pages/findings/FindingDetailPage";
import { FindingFormPage } from "./pages/findings/FindingFormPage";
import { FindingsListPage } from "./pages/findings/FindingsListPage";
import { FrameworkDetailPage } from "./pages/frameworks/FrameworkDetailPage";
import { FrameworkFormPage } from "./pages/frameworks/FrameworkFormPage";
import { FrameworksListPage } from "./pages/frameworks/FrameworksListPage";
import { RiskDetailPage } from "./pages/risks/RiskDetailPage";
import { RiskFormPage } from "./pages/risks/RiskFormPage";
import { RisksListPage } from "./pages/risks/RisksListPage";
import { VendorDetailPage } from "./pages/vendors/VendorDetailPage";
import { VendorFormPage } from "./pages/vendors/VendorFormPage";
import { VendorsListPage } from "./pages/vendors/VendorsListPage";
import { AuditLogPage } from "./pages/audit/AuditLogPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<PanelPage />} />

          <Route path="/activos" element={<AssetsListPage />} />
          <Route path="/activos/nuevo" element={<AssetFormPage modo="crear" />} />
          <Route path="/activos/:id" element={<AssetDetailPage />} />
          <Route path="/activos/:id/editar" element={<AssetFormPage modo="editar" />} />

          <Route path="/riesgos" element={<RisksListPage />} />
          <Route path="/riesgos/nuevo" element={<RiskFormPage modo="crear" />} />
          <Route path="/riesgos/:id" element={<RiskDetailPage />} />
          <Route path="/riesgos/:id/editar" element={<RiskFormPage modo="editar" />} />

          <Route path="/controles" element={<ControlsListPage />} />
          <Route path="/controles/nuevo" element={<ControlFormPage modo="crear" />} />
          <Route path="/controles/:id" element={<ControlDetailPage />} />
          <Route path="/controles/:id/editar" element={<ControlFormPage modo="editar" />} />

          <Route path="/marcos" element={<FrameworksListPage />} />
          <Route path="/marcos/nuevo" element={<FrameworkFormPage />} />
          <Route path="/marcos/:id" element={<FrameworkDetailPage />} />

          <Route path="/evidencias" element={<EvidenceListPage />} />
          <Route path="/evidencias/nueva" element={<EvidenceUploadPage />} />
          <Route path="/evidencias/:id" element={<EvidenceDetailPage />} />
          <Route path="/evidencias/:id/editar" element={<EvidenceEditPage />} />

          <Route path="/hallazgos" element={<FindingsListPage />} />
          <Route path="/hallazgos/nuevo" element={<FindingFormPage modo="crear" />} />
          <Route path="/hallazgos/:id" element={<FindingDetailPage />} />
          <Route path="/hallazgos/:id/editar" element={<FindingFormPage modo="editar" />} />

          <Route path="/acciones" element={<ActionsListPage />} />
          <Route path="/acciones/nueva" element={<ActionFormPage modo="crear" />} />
          <Route path="/acciones/:id" element={<ActionDetailPage />} />
          <Route path="/acciones/:id/editar" element={<ActionFormPage modo="editar" />} />

          <Route path="/proveedores" element={<VendorsListPage />} />
          <Route path="/proveedores/nuevo" element={<VendorFormPage modo="crear" />} />
          <Route path="/proveedores/:id" element={<VendorDetailPage />} />
          <Route path="/proveedores/:id/editar" element={<VendorFormPage modo="editar" />} />

          <Route path="/auditoria" element={<AuditLogPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default App;
