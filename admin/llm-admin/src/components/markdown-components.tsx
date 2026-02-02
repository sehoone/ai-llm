// Custom components for react-markdown
export const markdownComponents = {
  table: ({ node, ...props }: any) => (
    <div className='my-4 overflow-x-auto'>
      <table
        className='w-full border-collapse border border-border text-sm'
        {...props}
      />
    </div>
  ),
  thead: ({ node, ...props }: any) => <thead className='bg-muted' {...props} />,
  th: ({ node, ...props }: any) => (
    <th
      className='border border-border px-4 py-2 text-left font-semibold'
      {...props}
    />
  ),
  td: ({ node, ...props }: any) => (
    <td className='border border-border px-4 py-2' {...props} />
  ),
}
