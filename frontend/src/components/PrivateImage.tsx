import {useEffect, useState} from 'react';
import {ImageOff} from 'lucide-react';
import {privateAsset} from '../lib/api';

export function PrivateImage({path, alt, className}: {path: string; alt: string; className?: string}) {
  const [source, setSource] = useState<string>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true; let url = '';
    privateAsset(path).then((value) => {url = value; if (active) setSource(value);}).catch(() => active && setFailed(true));
    return () => {active = false; if (url) URL.revokeObjectURL(url);};
  }, [path]);
  if (failed) return <div className={`private-image-fallback ${className || ''}`}><ImageOff/><span>Evidence asset unavailable</span></div>;
  if (!source) return <div className={`private-image-loading ${className || ''}`}><i/><span>ACQUIRING PRIVATE MEDIA</span></div>;
  return <img className={className} src={source} alt={alt}/>;
}

