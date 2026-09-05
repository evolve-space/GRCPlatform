interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPaginas = Math.max(1, Math.ceil(total / pageSize));

  if (totalPaginas <= 1) {
    return null;
  }

  return (
    <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
      <p>
        Página {page} de {totalPaginas} · {total} resultados
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="rounded-md border border-slate-300 px-3 py-1.5 font-medium hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Anterior
        </button>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPaginas}
          className="rounded-md border border-slate-300 px-3 py-1.5 font-medium hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
