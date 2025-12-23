export default async function SandboxPage(props: {
  params: Promise<{ lang: string; version: string }>;
}) {
  const params = await props.params;
  
  return (
    <div>
      <h1>hello, world!</h1>
      <p>테스트용 페이지</p>
      <p>Language: {params.lang}</p>
      <p>Version: {params.version}</p>
    </div>
  );
}

